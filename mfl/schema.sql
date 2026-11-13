CREATE DATABASE IF NOT EXISTS mfl_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE mfl_db;

DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS payment_schedule;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS addresses;

-- ============================================================================
-- 1. ADDRESSES
-- ============================================================================
CREATE TABLE addresses (
    address_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    country         VARCHAR(60) NOT NULL DEFAULT 'India',
    state           VARCHAR(80) NOT NULL DEFAULT 'BIHAR',
    district        VARCHAR(80) NOT NULL DEFAULT 'MADHUBANI',
    police_station  VARCHAR(100) NULL,
    village         VARCHAR(100) NULL,
    mohalla         VARCHAR(100) NULL,
    ward_no         VARCHAR(30) NULL,
    landmark        VARCHAR(150) NULL,
    postal_code     VARCHAR(12) NOT NULL,

    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by      VARCHAR(64) NOT NULL,
    updated_by      VARCHAR(64) NOT NULL,
    version         INT UNSIGNED NOT NULL DEFAULT 1,

    INDEX idx_addr_location (state, district, postal_code),
    INDEX idx_addr_village (police_station, village, mohalla)
) ENGINE=InnoDB;

-- ============================================================================
-- 2. CUSTOMERS
-- ============================================================================
CREATE TABLE customers (
    customer_id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    customer_code           VARCHAR(30) NOT NULL,
    customer_name           VARCHAR(120) NOT NULL,
    guardian_name           VARCHAR(120) NOT NULL,
    guardian_relation       ENUM('FATHER', 'HUSBAND', 'MOTHER', 'OTHER') NOT NULL DEFAULT 'FATHER',
    guarantor_id            BIGINT UNSIGNED NULL,
    guarantor_relation      ENUM('FATHER', 'HUSBAND', 'MOTHER', 'OTHER') NOT NULL DEFAULT 'FATHER',
    guarantor_mobile        VARCHAR(15) NULL,
    customer_mobile         VARCHAR(15) NOT NULL,
    customer_email          VARCHAR(120) NULL,
    address_id              BIGINT UNSIGNED NOT NULL,

    aadhaar_no              CHAR(12) NULL,
    pan_no                  CHAR(10) NULL,
    aadhaar_img_s3_key      VARCHAR(512) NULL,
    pan_img_s3_key          VARCHAR(512) NULL,
    kyc_status              ENUM('NOT_UPLOADED', 'UPLOADED', 'PENDING', 'VERIFIED', 'REJECTED') NOT NULL DEFAULT 'NOT_UPLOADED',

    family_income           DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    family_loan             DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    customer_status         ENUM('ACTIVE', 'INACTIVE', 'BLACKLISTED') NOT NULL DEFAULT 'ACTIVE',
    customer_rating         BIGINT UNSIGNED NOT NULL DEFAULT 8,

    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by              VARCHAR(64) NOT NULL,
    updated_by              VARCHAR(64) NOT NULL,
    version                 INT UNSIGNED NOT NULL DEFAULT 1,

    UNIQUE KEY uk_customer_code (customer_code),
    UNIQUE KEY uk_customer_mobile (customer_mobile),
    UNIQUE KEY uk_customer_aadhaar (aadhaar_no),
    UNIQUE KEY uk_customer_pan (pan_no),
    INDEX idx_customer_address (address_id),
    INDEX idx_customer_guarantor (guarantor_id),
    INDEX idx_customer_status (customer_status, kyc_status),

    CONSTRAINT fk_customers_address
        FOREIGN KEY (address_id) REFERENCES addresses(address_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_customers_guarantor
        FOREIGN KEY (guarantor_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 3. LOANS
-- ============================================================================
CREATE TABLE loans (
    loan_id                     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    loan_account_no             VARCHAR(30) NOT NULL,
    loan_parent_id              BIGINT UNSIGNED NULL,
    customer_id                 BIGINT UNSIGNED NOT NULL,
    guarantor_id                BIGINT UNSIGNED NULL,

    rem_principal_amt               DECIMAL(15, 2) NOT NULL,
    original_principal_amt_k        DECIMAL(15, 5) NOT NULL,

    rate_of_interest            DECIMAL(6, 3) NOT NULL DEFAULT 2.000,

    borrowing_date              DATE NOT NULL,
    modified_borrowing_date     DATE NOT NULL,
    emi_start_date              DATE NULL,
    emi_first_installment_date  DATE NULL,
    emi_last_installment_date   DATE NULL,

    loan_type                   ENUM('EMI', 'MONTHLY_INTEREST', 'ONETIME') NOT NULL DEFAULT 'EMI',
    repayment_frequency         ENUM('MONTHLY', 'ONETIME') NOT NULL DEFAULT 'MONTHLY',
    total_no_of_kist              SMALLINT UNSIGNED NOT NULL DEFAULT 12,
    installment_amount          DECIMAL(15, 2) NOT NULL DEFAULT 6000.00,

    closed_date                 DATE NULL,
    additional_interest         DECIMAL(12, 3) NOT NULL DEFAULT 0.000,
    loan_status                 ENUM('DRAFT', 'ACTIVE', 'CLOSED', 'RESTRUCTURED', 'DEFAULTED') NOT NULL DEFAULT 'ACTIVE',

    manager_name                VARCHAR(120) NULL,
    manager_amount              DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    processing_fee              DECIMAL(12, 2) NOT NULL DEFAULT 200.00,
    owner_name                  VARCHAR(120) NULL,
    owner_amount                DECIMAL(15, 2) NOT NULL DEFAULT 0.00,

    loan_purpose                VARCHAR(150) NULL,
    fine_rule                   VARCHAR(255) NULL,
    description                 TEXT NULL,

    created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by                  VARCHAR(64) NOT NULL,
    updated_by                  VARCHAR(64) NOT NULL,
    version                     INT UNSIGNED NOT NULL DEFAULT 1,

    UNIQUE KEY uk_loan_account_no (loan_account_no),
    UNIQUE KEY uk_loans_id_customer (loan_id, customer_id),
    INDEX idx_loans_customer_status (customer_id, loan_status),
    INDEX idx_loans_guarantor (guarantor_id),
    INDEX idx_loans_parent (loan_parent_id),
    INDEX idx_loans_type_borrowing (loan_type, borrowing_date),

    CONSTRAINT chk_loans_rem_principal
        CHECK (rem_principal_amt >= 0),
    CONSTRAINT chk_loans_original_principal
        CHECK (original_principal_amt_k > 0),
    CONSTRAINT chk_loans_capital_split
        CHECK ((manager_amount + owner_amount) / 1000 = original_principal_amt_k),

    CONSTRAINT fk_loans_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_loans_guarantor
        FOREIGN KEY (guarantor_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_loans_parent
        FOREIGN KEY (loan_parent_id) REFERENCES loans(loan_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 4. PAYMENT_SCHEDULE (`balance_due` calculated strictly at runtime)
-- ============================================================================
CREATE TABLE payment_schedule (
    payment_schedule_id                          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    loan_id                         BIGINT UNSIGNED NOT NULL,
    loan_parent_id                  BIGINT UNSIGNED NULL,
    loan_type                       ENUM('EMI', 'MONTHLY_INTEREST', 'ONETIME') NOT NULL,
    current_kist_no                 SMALLINT UNSIGNED NOT NULL,
    installment_date                DATE NOT NULL,

    billing_year                    SMALLINT UNSIGNED GENERATED ALWAYS AS (YEAR(installment_date)) STORED,
    billing_month                   TINYINT UNSIGNED GENERATED ALWAYS AS (MONTH(installment_date)) STORED,

    installment_amount              DECIMAL(15, 2) NOT NULL,
    fine_amount                     DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    other_amount                    DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    partial_principal_amt_return    DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    kist_interest_amount            DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    forgive_amount                  DECIMAL(15, 2) NOT NULL DEFAULT 0.00,

    manager_name                    VARCHAR(120) NULL,
    manager_received_amount         DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    owner_name                      VARCHAR(120) NULL,
    owner_received_amount           DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    payer_name                      VARCHAR(120) NULL,
    amount_paid                     DECIMAL(15, 2) NOT NULL DEFAULT 0.00,

    remaining_principal_amt         DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    status                          ENUM('OPEN', 'PARTIAL', 'CLOSED', 'OVERDUE', 'WAIVED') NOT NULL DEFAULT 'OPEN',
    payment_date                    DATETIME NULL,

    created_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by                      VARCHAR(64) NOT NULL,
    updated_by                      VARCHAR(64) NOT NULL,
    version                         INT UNSIGNED NOT NULL DEFAULT 1,

    UNIQUE KEY uk_ps_loan_kist (loan_id, current_kist_no),
    UNIQUE KEY uk_ps_loan_year_month (loan_id, billing_year, billing_month),
    UNIQUE KEY uk_ps_id_loan (payment_schedule_id, loan_id),
    INDEX idx_ps_due_collection (status, installment_date),
    INDEX idx_ps_year_month (billing_year, billing_month, status),
    INDEX idx_ps_type_year_month (loan_type, billing_year, billing_month, status),
    INDEX idx_ps_parent_loan (loan_parent_id),

    CONSTRAINT chk_ps_received_split
        CHECK (manager_received_amount + owner_received_amount = amount_paid + forgive_amount),

    CONSTRAINT fk_ps_loan
        FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_ps_parent_loan
        FOREIGN KEY (loan_parent_id) REFERENCES loans(loan_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================================
-- 5. PAYMENTS (Immutable Collection / Receipt Ledger)
-- ============================================================================
CREATE TABLE payments (
    payment_id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    receipt_no              VARCHAR(40) NOT NULL,
    idempotency_key         VARCHAR(64) NOT NULL,
    payment_schedule_id                  BIGINT UNSIGNED NULL,
    loan_id                 BIGINT UNSIGNED NOT NULL,
    customer_id             BIGINT UNSIGNED NOT NULL,
    current_kist_no         SMALLINT UNSIGNED NULL,
    installment_date        DATE NULL,

    payment_amount          DECIMAL(15, 2) NOT NULL,
    payment_amt_k           DECIMAL(15, 3) GENERATED ALWAYS AS (payment_amount / 1000) VIRTUAL,
    payment_date            DATETIME NOT NULL,

    payment_mode            ENUM('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE') NOT NULL DEFAULT 'CASH',
    transaction_ref         VARCHAR(100) NULL,
    payment_status          ENUM('SUCCESS', 'REVERSED', 'BOUNCED') NOT NULL DEFAULT 'SUCCESS',
    remarks                 VARCHAR(255) NULL,

    created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by              VARCHAR(64) NOT NULL,
    updated_by              VARCHAR(64) NOT NULL,
    version                 INT UNSIGNED NOT NULL DEFAULT 1,

    UNIQUE KEY uk_payments_receipt (receipt_no),
    UNIQUE KEY uk_payments_idempotency (idempotency_key),
    INDEX idx_payments_loan (loan_id, payment_date),
    INDEX idx_payments_schedule (payment_schedule_id, loan_id),
    INDEX idx_payments_customer (customer_id),

    CONSTRAINT chk_payments_amount
        CHECK (payment_amount > 0),

    CONSTRAINT fk_payments_loan_customer
        FOREIGN KEY (loan_id, customer_id) REFERENCES loans(loan_id, customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_payments_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_payments_schedule_loan
        FOREIGN KEY (payment_schedule_id, loan_id) REFERENCES payment_schedule(payment_schedule_id, loan_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Monthly snapshot: one row per loan, purged and rebuilt on each report run.
CREATE TABLE payment_schedule_report (
    loan_id                         BIGINT UNSIGNED PRIMARY KEY,
    report_billing_year             SMALLINT UNSIGNED NOT NULL,
    report_billing_month            TINYINT UNSIGNED NOT NULL,
    report_run_date                 DATE NOT NULL,
    loan_parent_id                  BIGINT UNSIGNED NULL,
    loan_type                       ENUM('EMI', 'MONTHLY_INTEREST', 'ONETIME') NOT NULL,
    report_status                   ENUM('OPEN', 'OVERDUE', 'CLOSED') NOT NULL,
    borrower_name                   VARCHAR(120) NOT NULL,
    guardian_name                   VARCHAR(120) NOT NULL,
    borrower_mobile                 VARCHAR(15) NOT NULL,
    guarantor_name                  VARCHAR(120) NULL,
    guarantor_mobile                VARCHAR(15) NULL,
    mohalla                         VARCHAR(100) NULL,
    village                         VARCHAR(100) NULL,
    borrowing_date                  DATE NOT NULL,
    modified_borrowing_date         DATE NOT NULL,
    emi_start_date                  DATE NULL,
    emi_first_installment_date      DATE NULL,
    emi_last_installment_date       DATE NULL,
    total_no_of_kist                INT UNSIGNED NULL,
    manager_name                    VARCHAR(120) NULL,
    owner_name                      VARCHAR(120) NULL,
    rem_principal_amt               DECIMAL(15, 2) NOT NULL,
    current_payment_schedule_id     BIGINT UNSIGNED NULL,
    current_kist_no                 INT UNSIGNED NULL,
    installment_date                DATE NULL,
    billing_year                    SMALLINT UNSIGNED NULL,
    billing_month                   TINYINT UNSIGNED NULL,
    installment_amount              DECIMAL(15, 2) NULL,
    total_overdue_amount            DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    total_fine_amount               DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    total_interest_amount           DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    total_other_amount              DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    total_manager_paid_amount       DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    total_owner_paid_amount         DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    open_kist_count                 INT UNSIGNED NOT NULL DEFAULT 0,
    overdue_kist_count              INT UNSIGNED NOT NULL DEFAULT 0,
    created_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_psr_loan FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
