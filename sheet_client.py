"""Manages Google Sheets authentication, SSL verification, and data retrieval."""

import logging
from typing import Any, List
from config import SheetConfig
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
import gspread
import urllib3

logger = logging.getLogger(__name__)


class GoogleSheetClient:

    def __init__(self, config: SheetConfig):
        self.config = config
        self._client = self._authenticate()
        # self.spreadsheet = self._client.open(self.config.spreadsheet_name)

    def _authenticate(self) -> gspread.Client:
        """Authenticates using Service Account JSON with optional SSL verification bypass."""
        if self.config.disable_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        logger.info(
            f"Loading credentials from '{self.config.credentials_file}'..."
        )
        creds = Credentials.from_service_account_file(
            self.config.credentials_file, scopes=self.config.scopes
        )

        return gspread.Client(auth=creds)

    def fetch_range_data(self) -> List[List[Any]]:
        """Opens the configured sheet and fetches data from the specified range."""
        logger.info(
            f"Opening spreadsheet '{self.config.spreadsheet_name}', tab index"
            f" {self.config.worksheet_index}..."
        )
        spreadsheet = self._client.open(self.config.spreadsheet_name)
        worksheet = spreadsheet.get_worksheet(self.config.worksheet_index)

        logger.info(f"Fetching range: {self.config.data_range}...")
        data = worksheet.get(self.config.data_range)

        if not data:
            raise ValueError(
                f"No data returned for range {self.config.data_range} in"
                f" {self.config.spreadsheet_name}"
            )

        return data

    def get_worksheet_records(self,spreadsheet_name:str, worksheet_name: str) -> List[dict]:
        """Safely reads all existing data from a specific tab as a list of dictionaries."""
        spreadsheet = self._client.open(spreadsheet_name)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
            return []
        except Exception as e:
            logger.warning(f"Could not read existing rows from '{worksheet_name}': {e}. Assuming empty.")
            return []

    def append_unique_records(
            self, spreadsheet_name:str,worksheet_name: str, headers: List[str], rows: List[List[Any]], key_column_index: int
    ) -> None:
        """Reads existing sheet records, screens out duplicate keys, and appends only brand new rows."""
        try:
            # 1. Fetch or initialize the destination worksheet workspace
            spreadsheet = self._client.open(spreadsheet_name)
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                # If sheet exists but is entirely blank, set up the headers first
                if not worksheet.row_values(1):
                    worksheet.update([headers])
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Target worksheet '{worksheet_name}' not found. Creating it...")
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=len(headers))
                worksheet.update([headers])

            # 2. Extract existing tracking IDs to prevent creating duplicates
            existing_records = self.get_worksheet_records(spreadsheet_name,worksheet_name)
            key_name = headers[key_column_index]
            existing_keys = {str(row[key_name]).strip() for row in existing_records if key_name in row}

            # 3. Filter the payload loop matrix to separate old rows from brand new rows
            new_rows_to_append = []
            for row in rows:
                if not row:
                    continue
                row_key = str(row[key_column_index]).strip()
                if row_key not in existing_keys:
                    new_rows_to_append.append(row)

            # 4. Append only the brand new records in a single optimized block transaction
            if new_rows_to_append:
                worksheet.append_rows(new_rows_to_append, value_input_option="USER_ENTERED")
                logger.info(f"🚀 Successfully appended {len(new_rows_to_append)} brand new rows to '{worksheet_name}'.")
            else:
                logger.info(f"✨ No new data to append for '{worksheet_name}'. All records already exist.")

        except Exception as e:
            logger.error(f"Failed handling incremental storage updates on '{worksheet_name}': {e}")
            raise

    def overwrite_worksheet(self, spreadsheet_name:str, worksheet_name: str, headers: List[str], rows: List[List[Any]]) -> None:
        """Safely clears a worksheet target and writes a completely updated dataset."""
        try:
            # 1. Fetch or dynamically initialize worksheet target
            spreadsheet = self._client.open(spreadsheet_name)
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Target worksheet '{worksheet_name}' not found. Creating it dynamically...")
                # Create a basic canvas size; it grows automatically during update blocks
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=20)

            # 2. Clear out any legacy cell structures
            worksheet.clear()
            logger.info(f"Cleared existing records from worksheet table: '{worksheet_name}'")

            # 3. Consolidate payload matrix arrays
            payload = [headers] + rows

            # 4. Push full dataset via a single rapid grid update call
            worksheet.update(payload)
            logger.info(f"Successfully populated '{worksheet_name}' grid with {len(rows)} data rows.")

        except Exception as e:
            logger.error(f"Failed writing data block matrix into sheet workspace '{worksheet_name}': {e}")
            raise
