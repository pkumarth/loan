# MFL Core Service — Master Product & Engineering Specification

## 1. System Overview & Execution Pipeline
MFL Core Service is a microfinance lending backend managing borrower origination, schedule generation, and collections across 6 relational tables:
- **Stage 1 (Origination):** `1. addresses` ➔ `2. customers` ➔ `3. loans`
- **Stage 2 (Schedule Engine):** Active `EMI` and `MONTHLY_INTEREST` loans generate monthly rows in `4. payment_schedule` (on the 6th of every month).
- **Stage 3 (Collection Sync):** Updating collection amounts on `4. payment_schedule` records an immutable receipt transaction in `5. payments`.

## 2. Tech Stack & Deployment Architecture
- **Runtime & Framework:** Python 3.12+, FastAPI, Pydantic v2, Uvicorn (deployed on AWS ECS Fargate; managed via Astral `uv`).
- **ALB Path-Based Routing:**
  - `APP_ROOT_PREFIX`: `/mfl-core` | `API_V1_PREFIX`: `/api/v1` (Full base: `/mfl-core/api/v1`)
  - Health check: `GET /mfl-core/health` (`SELECT 1 AS ok`)
  - OpenAPI / Docs: `/mfl-core/docs`, `/mfl-core/redoc`, `/mfl-core/openapi.json`
- **Database & Pooling:** MySQL 8.0+ (`InnoDB`, `utf8mb4_unicode_ci`). Raw parameterized SQL only via `PyMySQL` (`DictCursor`) + `DBUtils.PooledDB` (`autocommit=False`, `ping=1`, `blocking=True`) + `cryptography`. **No ORM.**
- **Layered Architecture (`mfl/app/`):** `core/` (config, database, exceptions) ➔ `util/` (response envelope, field projection) ➔ `domain/` (Pydantic schemas, enums, column whitelists) ➔ `dao/` (reusable `BaseDAO` + module DAOs) ➔ `service/` (business logic & validations) ➔ `api/v1/` (FastAPI routers) ➔ `main.py`.

## 3. Global API Contracts (Mandatory Across All Modules)
1. **Unified JSON Envelope (All `2xx` & `4xx`/`5xx` Responses):**
   ```json
   {
     "status": "success | failure | partial_success | processing",
     "status_code": 200,
     "display_msg": "Human-readable message",
     "cause": "success | ERROR_CODE",
     "data": {},
     "pagination": {"page": 1, "size": 30, "total_elements": 100, "total_pages": 4, "has_next": true}
   }
   ```
2. **Audit & Optimistic Locking:**
   - Actor extracted from `X-User-Id` header (defaults to `"SYSTEM"`).
   - On `INSERT`: `created_by = actor`, `updated_by = actor` (**never `NULL`**), `version = 1`.
   - On `PUT` / `PATCH`: `updated_by = actor`, `version = version + 1`. If `version` is passed in payload, enforce `WHERE ... AND version = %s` (return `409 OPTIMISTIC_LOCK_CONFLICT` on mismatch).
3. **Field Projection (`GET /{id}` & `GET ""`):**
   - Audit columns: `created_at`, `updated_at`, `created_by`, `updated_by`, `version`.
   - **Default (no `include`/`exclude`):** Exclude all 5 audit columns.
   - **`?include=a,b`:** Return ONLY listed columns.
   - **`?exclude=a,b`:** Return ALL columns (including audit columns) EXCEPT listed columns.
   - Passing both `include` and `exclude` or invalid column names returns `400`.
4. **Bulk `GET ""` Rules:**
   - Payment schedule list (`GET /payment-schedules`) needs no filter: with none it returns the first 30 rows (default page size) sorted by `installment_date DESC, payment_schedule_id DESC`. `GET /addresses`, `GET /customers` and `GET /loans` behave the same way: with no filter they return the latest 30 rows (`address_id DESC` / `customer_id DESC` / `loan_id DESC`).
   - Pagination defaults: `page=1`, `size=30` (`max=200`), sorted `DESC` by primary key.
   - Bulk add (`POST /_bulk`) is **not** permitted.
5. **Mutation Endpoints per Resource:**
   - `POST ""` (Create single), `PUT "/{id}"` (Full update), `PATCH "/{id}"` (Strictly **1 business field** per call; `422` if `0` or `>1` fields sent), `DELETE "/{id}"` (`409` if child FK rows exist).
   - Blank strings `""` in payloads automatically sanitize to `None` (`NULL`).

## 4. Module Business Rules & Formulas
### 4.1 Addresses (`/mfl-core/api/v1/addresses`)
- Defaults: `country='India'`, `state='BIHAR'`, `district='MADHUBANI'`. Mandatory: `postal_code`.
- Filters: `address_ids` (CSV), `country`, `state`, `district`, `police_station`, `village`, `mohalla`, `ward_no`, `postal_code`.

### 4.2 Customers (`/mfl-core/api/v1/customers`)
- Auto-generates `customer_code` (`CUST-YYYYMMDD-XXXXXX`) if omitted.
- Column `customer_rating` (`BIGINT UNSIGNED NOT NULL DEFAULT 8`).
- Self-FK `guarantor_id -> customers(customer_id)`, FK `address_id -> addresses(address_id)`.
- Unique keys: `customer_code`, `customer_mobile`, `aadhaar_no`, `pan_no`.
- Payload aliases: `guarantorId`/`gurantorId` ➔ `guarantor_id`, `addressId` ➔ `address_id`.
- Filters: `customer_ids` (CSV), `customer_code`, `customer_name` (`LIKE`), `customer_mobile`, `address_id`, `guarantor_id`, `aadhaar_no`, `pan_no`, `kyc_status`, `customer_status`.

### 4.3 Loans (`/mfl-core/api/v1/loans`)
- Auto-generates `loan_account_no` (`LN-YYYYMMDD-XXXXXX`) if omitted.
- Default `rate_of_interest` when omitted: `2.000` for all loan types. An explicit value is always kept.
- `customer_id` (`customerId`) is mandatory; `guarantor_id` (`guarantorId`/`gurantorId`) is **optional (`NULL`)**.
- Payload aliases: `parent_loan_id`/`parentLoanId` ➔ `loan_parent_id`; `monthly_amount`/`monthlyAmount` ➔ `installment_amount`.
- Payload naming: the create, PUT and PATCH request field is `principal_amt` (rupees). The server stores it as `rem_principal_amt` and derives `original_principal_amt_k = principal_amt / 1000`. Sending `rem_principal_amt` in a request body is rejected with 422. Responses return the DB names `rem_principal_amt` and `original_principal_amt_k`.
- Naming: `rem_principal_amt` = current principal (changes only through ONETIME settlement). `original_principal_amt_k` = `principal / 1000` stored once at creation (`DECIMAL(15,5)`, never changes). `modified_borrowing_date` = interest start date (equals `borrowing_date` at creation, moves to the hisab date after each settlement; `borrowing_date` is never changed by settlement).
- Free-text columns: `loan_purpose`, `fine_rule` (reference only, no calculation), `description` (editable).
- **Capital Split Invariant (POST & DB CHECK), in k with no rounding:** `(manager_amount + owner_amount) / 1000 == original_principal_amt_k`.
- **Protected after creation (PUT & PATCH → `400 LOAN_FIELD_PROTECTED`):** `rem_principal_amt`, `original_principal_amt_k`, `modified_borrowing_date`, `manager_amount`, `owner_amount`. Only the ONETIME settlement changes `rem_principal_amt` and `modified_borrowing_date`.
- **Parent rule:** a root loan has `loan_parent_id = loan_id` (set at creation, never changed). `loan_parent_id` is not used for kist numbering.
- **Loan status:** stays `ACTIVE` while `rem_principal_amt > 0`; becomes `CLOSED` with `closed_date` = hisab date when it reaches 0.
- **Schedule & Date Rules by `loan_type` (using calendar-accurate `add_months`):**
  - `EMI`: `repayment_frequency=MONTHLY`, `total_no_of_kist=12` (defaults). `emi_start_date = emi_start_date or borrowing_date`. Auto-computes `emi_first_installment_date = add_months(emi_start_date, 1)` and `emi_last_installment_date = add_months(emi_start_date, total_no_of_kist)`.
  - `MONTHLY_INTEREST`: `repayment_frequency=MONTHLY`, `emi_start_date = emi_start_date or borrowing_date`; `emi_first_installment_date = NULL`, `emi_last_installment_date = NULL`.

### 4.4 Payment Schedule (`/mfl-core/api/v1/payment-schedules`)
- Table name: `payment_schedule` (PK `payment_schedule_id`).
- `loan_type` (`ENUM('EMI','MONTHLY_INTEREST','ONETIME') NOT NULL`) is **always copied from `loans`**.
- Multi-year monthly uniqueness: STORED generated `billing_year = YEAR(installment_date)` and `billing_month = MONTH(installment_date)` with `UNIQUE(loan_id, billing_year, billing_month)` and `UNIQUE(loan_id, current_kist_no)`.
- **Received Split Invariant (POST, PUT, PATCH & DB CHECK):** `manager_received_amount + owner_received_amount == amount_paid + forgive_amount` (so `amount_paid = manager + owner - forgive`).
- `payer_name`: stored only on the schedule row; defaults to the borrower's name when not given.
- **Manual `remaining_principal_amt`:** Never auto-computed; allowed (> 0) ONLY when `loan_type IN ('MONTHLY_INTEREST', 'ONETIME')`; rejected (`400`) for `EMI` loans.
- **Runtime-Only `balance_due` (NOT stored in MySQL):**
  `balance_due = installment_amount + fine_amount + other_amount + kist_interest_amount - amount_paid` (forgive is already netted in `amount_paid`, so it is not subtracted again).
- **Unified Enriched Output:** All `GET`, `POST`, `PUT`, `PATCH`, and `generate-monthly` responses join `payment_schedule` + `loans` + `customers` (borrower) + `addresses` (`mohalla`, `village`) + `customers` (guarantor via `COALESCE(l.guarantor_id, c.guarantor_id)`).
- **6th-of-Month Batch Generator (`POST /payment-schedules/generate-monthly`):**
  - Scans `loans` where `loan_type IN ('EMI', 'MONTHLY_INTEREST')`, `loan_status = 'ACTIVE'`, and `COALESCE(emi_start_date, borrowing_date) < first_day_of_billing_month`.
  - Skips if `(loan_id, billing_year, billing_month)` already exists.
  - Due date: if `cycle_12_start_day <= day(effective_start_date) <= cycle_12_cutoff_day` (defaults `8` and `20`) ➔ `12th` of month; otherwise (day `21`–`31` or `1`–`7`) ➔ `25th` of month. Applies to `EMI` and `MONTHLY_INTEREST` only; `ONETIME` is not generated here.
  - `current_kist_no = round_half_up((due_date - effective_start_date).days / 30.4375)`. Must be `>= 1`.
  - `ONETIME`: `repayment_frequency=ONETIME`, `total_no_of_kist=1`; all three EMI dates `NULL`.
  - For `EMI`: stops if `generated_kists >= total_no_of_kist` or `current_kist_no > total_no_of_kist`. For `MONTHLY_INTEREST`: no upper cap while `ACTIVE`.
  - Copies `installment_amount`, `loan_type`, `loan_parent_id`, `manager_name`, and `owner_name` directly from `loans`; sets `kist_interest_amount = 0.00` and `fine_amount = 0.00` (reserved for overdue calculation API). Supports `dry_run: bool`. Response: `dry_run` → `200` ("Dry-run preview for YYYY-MM: N entries would be generated"); entries created → `201` ("Generated N schedule entries for YYYY-MM"); nothing created → `200` with the reasons (already generated / kists completed / not due yet).

### 4.4b Overdue Compute (`POST /payment-schedules/overdue-compute`)
Runs after the EMI / MONTHLY_INTEREST generator. Body (all optional): `loan_id`, `run_date` (default today), `dry_run` (default false). Scope: schedule rows with `loan_type IN ('EMI','MONTHLY_INTEREST')`, row `status <> 'CLOSED'`, loan `ACTIVE`. An unknown `loan_id` returns `404 LOAN_NOT_FOUND`.
- **Status lifecycle:** generated rows start `OPEN`. `OVERDUE` when the due is still greater than zero and `run_date > installment_date` (covers an unpaid installment and a fine or interest still outstanding after the installment is paid). `CLOSED` when the computed due is zero or less.
- **EMI, unpaid and past installment date:**
  - `fine_amount = 1% of loans.rem_principal_amt`, applied once (only while `fine_amount = 0`), whole rupees half up.
  - `kist_interest_amount = days x (installment_amount - amount_paid) x 2.5 / 3000`, where `days = run_date - installment_date`, whole rupees half up. Recalculated on every run.
- **EMI, installment fully paid:** no new fine or interest; interest is 0.
- **MONTHLY_INTEREST:** no fine and no interest.
- **Due (computed, not stored):** `installment_amount + fine_amount + other_amount + kist_interest_amount - amount_paid`. Forgive is not subtracted again, since `amount_paid` already nets it out.
- **Stored on non-dry runs:** `fine_amount`, `kist_interest_amount`, `status`, `version + 1`, `updated_by`. Due is never stored.
- **Response:** `run_date`, `dry_run`, `loan_id`, `row_count`, `total_due`, `loans` (per loan `row_count` and `total_due`, CLOSED rows excluded), `items` (per row figures and previous/new status).

### 4.4c Monthly Payment Schedule Report (`POST /payment-schedules/report-generate`)
Run manually once a month. Body (all optional): `billing_year`, `billing_month` (default current month), `dry_run` (default false). `run_date` is today.
- **Order:** the overdue computation (4.4b) runs first, so the stored figures are current. Then the report table is purged and rebuilt in the same transaction. If any step fails, the transaction rolls back and the previous report remains.
- **Scope:** `loan_status = ACTIVE` loans of type `EMI` or `MONTHLY_INTEREST`, plus `ONETIME` loans with `modified_borrowing_date` more than 11 months before today. Loans with no schedule rows yet are included with `report_status = OPEN` and zero totals.
- **Table `payment_schedule_report`:** exactly one row per `loan_id` (primary key). Stores borrower, guardian, mobile, guarantor, mohalla, village, loan dates, kist counts, manager and owner names, and `rem_principal_amt`, so no joins are needed when reading it.
- **Current row:** the earliest open row (not `CLOSED`). If there are no open rows, the last row by installment date.
- **Totals:** `total_overdue_amount`, `total_fine_amount`, `total_interest_amount`, `total_other_amount` are summed over open rows only. Manager and owner paid totals are summed over all rows of the loan. `open_kist_count` and `overdue_kist_count` count open and overdue rows.
- **Status:** `OVERDUE` if any open row is overdue, `OPEN` if open rows exist and none are overdue, `CLOSED` if the loan has rows and none are open.
- **File:** `{REPORT_DIR}/payment_schedule_report_{MM}_{YYYY}.tsv` (`REPORT_DIR` defaults to `reports`), written from the same rows, with a header line. Dry run writes neither the table nor the file.

### 4.4a ONETIME Settlement (`/mfl-core/api/v1/payment-schedules/onetime-*`)
Applies only to `loan_type = 'ONETIME'` loans with `loan_status = 'ACTIVE'`.
- **Interest:** `days = hisab_date - modified_borrowing_date`; `interest = days x rem_principal_amt x rate_of_interest / 3000` (rate is a monthly %, so this is per-day `P x R / 3000`), rounded half up to a whole rupee. Hisab date defaults to today. Hisab date before `modified_borrowing_date` → `400 HISAB_DATE_BEFORE_INTEREST_START`.
- **Dry run, all loans:** `POST /payment-schedules/onetime-dry-run?page=&size=` with optional `hisab_date`. Paginated (default 30, max 200). Returns, per active ONETIME loan, `customer_name`, `guardian_name` (from the customer), `days` (hisab date minus `modified_borrowing_date`), `per_day_interest` (`rem_principal_amt x rate_of_interest / 3000`, shown to 2 decimals), `interest_amount` and `total_due = rem_principal_amt + interest_amount`. Reads the loan table only; writes nothing.
- **Settlement, one loan:** `POST /payment-schedules/onetime-settlement`. `loan_id` is mandatory. `dry_run: true` returns `guardian_name`, `days`, `per_day_interest`, the interest, total due and next `current_kist_no` without writing. The real-run response also includes `guardian_name`, `days` and `per_day_interest`. A real run takes `hisab_date`, `manager_received_amount`, `owner_received_amount`, `forgive_amount` (default 0) and `payer_name`.
  - `amount_paid = manager_received_amount + owner_received_amount - forgive_amount`; negative → `400 AMOUNT_PAID_NEGATIVE`.
  - `partial = max(0, amount_paid - interest)`; `shortfall = max(0, interest - amount_paid)`.
  - `partial > rem_principal_amt` → `400 PARTIAL_EXCEEDS_PRINCIPAL`.
  - A second settlement in the same billing month → `409 DUPLICATE_MONTHLY_SCHEDULE`.
  - New `rem_principal_amt = rem_principal_amt - partial + shortfall`.
  - Writes one `payment_schedule` row: `installment_amount = interest`, `installment_date = payment_date = hisab_date`, `partial_principal_amt_return = partial`, `forgive_amount`, `amount_paid`, `remaining_principal_amt = new rem_principal_amt`, `status = CLOSED`, `current_kist_no = existing rows for the loan + 1`, `loan_parent_id` copied from the loan, and `payer_name`.
  - Updates the loan in the same transaction: `rem_principal_amt`, `modified_borrowing_date = hisab_date`, status (`ACTIVE` or `CLOSED` at zero), `closed_date`. Manager and owner amounts are not changed.
- Response codes: dry run `200`; settlement `201`.

### 4.5 Payments (`payments`)
- `payments`: Immutable receipt log (`receipt_no`, `idempotency_key`, virtual `payment_amt_k`) with composite FKs `(loan_id, customer_id)`, `(payment_schedule_id, loan_id) -> payment_schedule`. Whenever collection updates `payment_schedule`, insert into `payments` in the same DB transaction.
