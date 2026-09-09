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

    authed_session = AuthorizedSession(creds)
    if self.config.disable_ssl:
      authed_session.verify = False
      authed_session.auth_request.session.verify = False

    return gspread.Client(auth=creds, session=authed_session)

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
