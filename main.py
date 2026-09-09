"""Entrypoint to execute Google Sheet extraction, transformation, dual-destination TSV, and Cloud incremental update routing."""

import csv
import logging
from typing import Any, List
from config import SheetConfig
from processor import LoanDataProcessor
from sheet_client import GoogleSheetClient

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def write_local_tsv(file_path: str, headers: List[str], rows: List[List[Any]]) -> None:
    """Writes structured rows safely into a local Tab-Separated Values (TSV) file in UTF-8."""
    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(headers)
            writer.writerows(rows)
        logger.info(f"💾 Generated Local TSV: '{file_path}' ({len(rows)} records stored).")
    except Exception as e:
        logger.error(f"❌ Failed generating local file storage mapping '{file_path}': {e}")
        raise


def main():
    config = SheetConfig()

    try:
        # 1. Fetch raw data from Google Sheets source range
        client = GoogleSheetClient(config)
        raw_data = client.fetch_range_data()

        # 2. Process data into typed Domain Objects
        processor = LoanDataProcessor(config)
        master_loans, payment_records = processor.process(raw_data)

        # Convert domain payloads to standardized list matrices once to reuse across targets
        master_rows = [loan.to_tsv_row() for loan in master_loans]
        payment_rows = [payment.to_tsv_row() for payment in payment_records]

        # Explicit schemas for our destination targets
        master_headers = [
            "loan_number",
            "borrower_name",
            "guardian_name",
            "mohalla",
            "mobile",
            "principal_amt_in_words",
            "principal_amt",
            "loan_disbursement_date",
            "loan_first_due_date",
            "loan_maturity_date",
            "total_installment",
            "installment_amount",
        ]

        payment_headers = [
            "payment_id",
            "loan_number",
            "borrower_name",
            "guardian_name",
            "mohalla",
            "mobile",
            "principal_amt_in_words",
            "principal_amt",
            "loan_disbursement_date",
            "loan_first_due_date",
            "loan_maturity_date",
            "total_installment",
            "installment_amount",
            "payment_date",
            "payment_mode",
            "paid_to_pkt",
            "paid_to_bhikhari",
            "raw_cell_value",
        ]

        # =========================================================================
        # DESTINATION TARGET 1: LOCAL DISK STORAGE (TSV OUTPUT)
        # =========================================================================
        logger.info("Executing local TSV data dumps...")
        write_local_tsv(config.master_tsv_path, master_headers, master_rows)
        write_local_tsv(config.payment_tsv_path, payment_headers, payment_rows)

        # =========================================================================
        # DESTINATION TARGET 2: LIVE INCREMENTAL CLOUD SHEET SYNC
        # =========================================================================
        logger.info("Executing incremental updates back to Google Sheet worksheets...")

        # Sync loans: screens column index 0 ("loan_number") to block duplicate keys
        client.append_unique_records(
            config.loan_spreadsheet,
            config.loan_worksheet,
            master_headers,
            master_rows,
            key_column_index=0
        )

        # Sync payments: screens column index 0 ("payment_id") to block duplicate keys
        client.append_unique_records(
            config.payment_spreadsheet,
            config.payment_worksheet,
            payment_headers,
            payment_rows,
            key_column_index=0
        )

        logger.info("🎉 Dual-destination ETL Pipeline executed successfully!")

    except Exception as e:
        logger.error(f"💥 ETL pipeline failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
