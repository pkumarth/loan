#!/usr/bin/env bash
# All API requests for the MFL core service.
# Usage: set the IDs below, then run each block (or copy one curl at a time).
# Start the server first:
#   uv run --env-file .env uvicorn app.main:app --host 127.0.0.1 --port 8000

BASE=http://127.0.0.1:8000
API=$BASE/mfl-core/api/v1
H='Content-Type: application/json'
U='X-User-Id: praveen'

# IDs to fill in after creating records
ADDRESS_ID=1
CUSTOMER_ID=1
GUARANTOR_ID=2
EMI_LOAN_ID=1
MI_LOAN_ID=2
ONETIME_LOAN_ID=3
SCHEDULE_ID=1

# ---------------------------------------------------------------- health
curl -s "$BASE/mfl-core/health"

# ---------------------------------------------------------------- addresses
# Create address
curl -s -X POST "$API/addresses" -H "$H" -H "$U" -d '{
  "country": "India", "state": "BIHAR", "district": "MADHUBANI",
  "police_station": "TESTPS", "village": "TESTVILLAGE", "mohalla": "TESTMOHALLA",
  "ward_no": "3", "landmark": "NEAR TEMPLE", "postal_code": "847101"
}'

# List addresses (paginated)
curl -s "$API/addresses?page=1&size=10" -H "$U"

# Get one address
curl -s "$API/addresses/$ADDRESS_ID" -H "$U"

# Update address (PUT: send full body)
curl -s -X PUT "$API/addresses/$ADDRESS_ID" -H "$H" -H "$U" -d '{
  "country": "India", "state": "BIHAR", "district": "MADHUBANI",
  "police_station": "TESTPS", "village": "TESTVILLAGE", "mohalla": "TESTMOHALLA",
  "ward_no": "3", "landmark": "NEAR TEMPLE", "postal_code": "847101"
}'

# Patch one address field
curl -s -X PATCH "$API/addresses/$ADDRESS_ID" -H "$H" -H "$U" -d '{"landmark": "OPPOSITE SCHOOL"}'

# Delete address (fails with 409 if a customer uses it)
curl -s -X DELETE "$API/addresses/$ADDRESS_ID" -H "$U"

# ---------------------------------------------------------------- customers
# Create borrower
curl -s -X POST "$API/customers" -H "$H" -H "$U" -d '{
  "customer_name": "RAJEEV MAHATO", "guardian_name": "NANDLAL MAHATO", "guardian_relation": "FATHER",
  "customer_mobile": "9876543210", "address_id": 1,
  "guarantor_id": 2, "guarantor_relation": "FATHER"
}'

# Create guarantor (no guarantor of their own)
curl -s -X POST "$API/customers" -H "$H" -H "$U" -d '{
  "customer_name": "GUARANTOR NAME", "guardian_name": "GUARANTOR GUARDIAN",
  "customer_mobile": "9123456780", "address_id": 1
}'

# List customers (paginated)
curl -s "$API/customers?page=1&size=10" -H "$U"

# Get one customer
curl -s "$API/customers/$CUSTOMER_ID" -H "$U"

# Update customer (PUT: send full body)
curl -s -X PUT "$API/customers/$CUSTOMER_ID" -H "$H" -H "$U" -d '{
  "customer_name": "RAJEEV MAHATO", "guardian_name": "NANDLAL MAHATO", "guardian_relation": "FATHER",
  "customer_mobile": "9876543210", "address_id": 1, "guarantor_id": 2, "guarantor_relation": "FATHER"
}'

# Patch one customer field
curl -s -X PATCH "$API/customers/$CUSTOMER_ID" -H "$H" -H "$U" -d '{"guardian_name": "NEW GUARDIAN"}'

# Delete customer (fails if loans reference it)
curl -s -X DELETE "$API/customers/$CUSTOMER_ID" -H "$U"

# ---------------------------------------------------------------- loans
# Create EMI loan (principal_amt in rupees; manager + owner must equal it)
curl -s -X POST "$API/loans" -H "$H" -H "$U" -d '{
  "customer_id": 1, "principal_amt": 12000, "borrowing_date": "2026-09-01",
  "emi_start_date": "2026-09-01", "manager_amount": 7000, "owner_amount": 5000,
  "loan_type": "EMI", "total_no_of_kist": 12, "installment_amount": 1000
}'

# Create MONTHLY_INTEREST loan
curl -s -X POST "$API/loans" -H "$H" -H "$U" -d '{
  "customer_id": 1, "principal_amt": 8000, "borrowing_date": "2026-09-01",
  "manager_amount": 4000, "owner_amount": 4000, "loan_type": "MONTHLY_INTEREST"
}'

# Create ONETIME loan
curl -s -X POST "$API/loans" -H "$H" -H "$U" -d '{
  "customer_id": 1, "principal_amt": 10000, "borrowing_date": "2026-09-15",
  "manager_amount": 6000, "owner_amount": 4000, "loan_type": "ONETIME"
}'

# List loans (paginated)
curl -s "$API/loans?page=1&size=10" -H "$U"

# Get one loan
curl -s "$API/loans/$EMI_LOAN_ID" -H "$U"

# Update loan (PUT: send full body; changing principal/manager/owner returns 400)
curl -s -X PUT "$API/loans/$EMI_LOAN_ID" -H "$H" -H "$U" -d '{
  "customer_id": 1, "principal_amt": 12000, "borrowing_date": "2026-09-01",
  "emi_start_date": "2026-09-01", "manager_amount": 7000, "owner_amount": 5000,
  "loan_type": "EMI", "total_no_of_kist": 12, "installment_amount": 1000, "rate_of_interest": 2.0
}'

# Patch one loan field (rate, purpose, etc.; principal_amt returns 400)
curl -s -X PATCH "$API/loans/$EMI_LOAN_ID" -H "$H" -H "$U" -d '{"rate_of_interest": 2.5}'

# Delete loan (fails with 409 if schedule rows or child loans exist)
curl -s -X DELETE "$API/loans/$ONETIME_LOAN_ID" -H "$U"

# ---------------------------------------------------------------- payment schedules
# Create schedule row (manager + owner received must equal amount_paid + forgive)
curl -s -X POST "$API/payment-schedules" -H "$H" -H "$U" -d '{
  "loan_id": 1, "current_kist_no": 1, "installment_date": "2026-10-12",
  "installment_amount": 1000, "amount_paid": 0, "forgive_amount": 0,
  "manager_received_amount": 0, "owner_received_amount": 0
}'

# List schedule rows (filters: loan_id, customer_id, loan_type, status, billing_year, billing_month, ...)
curl -s "$API/payment-schedules?page=1&size=10" -H "$U"
curl -s "$API/payment-schedules?loan_id=$EMI_LOAN_ID" -H "$U"

# Get one schedule row
curl -s "$API/payment-schedules/$SCHEDULE_ID" -H "$U"

# Update schedule row (PUT: send full body)
curl -s -X PUT "$API/payment-schedules/$SCHEDULE_ID" -H "$H" -H "$U" -d '{
  "loan_id": 1, "current_kist_no": 1, "installment_date": "2026-10-12",
  "installment_amount": 1000, "amount_paid": 500, "forgive_amount": 0,
  "manager_received_amount": 250, "owner_received_amount": 250
}'

# Patch one schedule field (exactly one field per request)
curl -s -X PATCH "$API/payment-schedules/$SCHEDULE_ID" -H "$H" -H "$U" -d '{"payer_name": "RAMESH"}'

# Delete schedule row
curl -s -X DELETE "$API/payment-schedules/$SCHEDULE_ID" -H "$U"

# Generate monthly EMI / MONTHLY_INTEREST rows (dry run first)
curl -s -X POST "$API/payment-schedules/generate-monthly" -H "$H" -H "$U" -d '{"dry_run": true}'

# Generate for a specific month (real run; leave out dry_run or set false)
curl -s -X POST "$API/payment-schedules/generate-monthly" -H "$H" -H "$U" -d '{
  "billing_year": 2026, "billing_month": 11, "cycle_12_start_day": 8, "cycle_12_cutoff_day": 20, "dry_run": false
}'

# ONETIME dry run for all active ONETIME loans (paginated; hisab_date optional, defaults to today)
curl -s -X POST "$API/payment-schedules/onetime-dry-run?page=1&size=10" -H "$H" -H "$U" -d '{"hisab_date": "2026-11-14"}'

# ONETIME settlement, dry run for one loan (no writes)
curl -s -X POST "$API/payment-schedules/onetime-settlement" -H "$H" -H "$U" -d '{
  "loan_id": 3, "hisab_date": "2026-11-14", "dry_run": true,
  "manager_received_amount": 0, "owner_received_amount": 0, "forgive_amount": 0
}'

# ONETIME settlement, real run (201; manager + owner received = paid + forgive)
curl -s -X POST "$API/payment-schedules/onetime-settlement" -H "$H" -H "$U" -d '{
  "loan_id": 3, "hisab_date": "2026-11-14", "dry_run": false,
  "manager_received_amount": 500, "owner_received_amount": 500, "forgive_amount": 0,
  "payer_name": "RAMESH"
}'

# Overdue compute for all EMI / MONTHLY_INTEREST open rows (run_date defaults to today)
curl -s -X POST "$API/payment-schedules/overdue-compute" -H "$H" -H "$U" -d '{"dry_run": true}'

# Overdue compute for one loan (real run; updates fine, interest, status)
curl -s -X POST "$API/payment-schedules/overdue-compute" -H "$H" -H "$U" -d '{"loan_id": 1}'

# Monthly report (rebuilds payment_schedule_report and writes the TSV file; dry run writes nothing)
curl -s -X POST "$API/payment-schedules/report-generate" -H "$H" -H "$U" -d '{"dry_run": true}'
curl -s -X POST "$API/payment-schedules/report-generate" -H "$H" -H "$U" -d '{"billing_year": 2026, "billing_month": 11, "dry_run": false}'
