"""Service module to cleanly look up and isolate loan details and payments from live Google Sheet tabs."""

import logging
from typing import Any, Dict, Optional
from config import SheetConfig
from sheet_client import GoogleSheetClient

logger = logging.getLogger(__name__)


class LoanSearchService:

    def __init__(self, client: GoogleSheetClient):
        """Initializes with an active, authenticated GoogleSheetClient instance."""
        self.client = client
        self.config = client.config

    def search_by_loan_id(self, loan_id: str) -> Optional[Dict[str, Any]]:
        """Queries the live 'loan' and 'payment' worksheets for a specific zero-padded Loan ID.

        Returns a structured payload containing loan metadata and chronologically sorted payments.
        """
        # Formats input IDs securely to match the database padding layout (e.g., "1001" -> "001001")
        target_id = str(loan_id).strip().zfill(6)
        logger.info(f"🔍 Initiating live sheet lookup for Loan ID: '{target_id}'...")

        # 1. Pull data arrays directly from cloud tables
        existing_loans = self.client.get_worksheet_records(self.config.loan_spreadsheet,self.config.loan_worksheet)
        existing_payments = self.client.get_worksheet_records(self.config.payment_spreadsheet,self.config.payment_worksheet)

        # 2. Extract target matching loan metadata profile
        loan_profile = next(
            (row for row in existing_loans if str(row.get("loan_number", "")).strip().zfill(6) == target_id),
            None
        )

        if not loan_profile:
            logger.warning(f"❌ Loan ID '{target_id}' could not be located in the 'loan' tab records.")
            return None

        # 3. Filter out all historical transaction rows matching this loan number
        related_transactions = [
            row for row in existing_payments
            if str(row.get("loan_number", "")).strip().zfill(6) == target_id
        ]

        # 4. Sort payments chronologically by the 'payment_date' string property
        def parse_chronological_index(pay_row: Dict[str, Any]) -> str:
            date_str = str(pay_row.get("payment_date", "")).strip()
            # Converts 'MM-DD-YYYY' internally into 'YYYY-MM-DD' for precise alphanumeric sorting
            if len(date_str) == 10 and "-" in date_str:
                parts = date_str.split("-")
                return f"{parts[2]}-{parts[0]}-{parts[1]}"
            return date_str

        related_transactions.sort(key=parse_chronological_index)

        # 5. Pack everything neatly into a structured return dictionary
        return {
            "loan_metadata": loan_profile,
            "total_payments_count": len(related_transactions),
            "payments": related_transactions
        }
