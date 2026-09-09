"""Entrypoint to execute Google Sheet extraction, transformation, and TSV export."""

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


def write_tsv(file_path: str, headers: List[str], rows: List[List[Any]]) -> None:
  """Writes structured rows to a Tab-Separated Values (TSV) file in UTF-8."""
  with open(file_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(headers)
    writer.writerows(rows)
  logger.info(f"Generated TSV: '{file_path}' ({len(rows)} records).")


def main():
  config = SheetConfig()

  try:
    # 1. Fetch raw data from Sheets
    client = GoogleSheetClient(config)
    raw_data = client.fetch_range_data()

    # 2. Process data into typed Domain Objects
    processor = LoanDataProcessor(config)
    master_loans, payment_records = processor.process(raw_data)

    # 3. Export Master Loans TSV
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
    write_tsv(
        config.master_tsv_path,
        master_headers,
        [loan.to_tsv_row() for loan in master_loans],
    )

    # 4. Export Payments TSV
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
    write_tsv(
        config.payment_tsv_path,
        payment_headers,
        [payment.to_tsv_row() for payment in payment_records],
    )

    logger.info("Pipeline executed successfully!")

  except Exception as e:
    logger.error(f"ETL pipeline failed: {e}", exc_info=True)


if __name__ == "__main__":
  main()
