"""Configuration settings and constants for Google Sheets ETL."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class SheetConfig:
  # Auth & Sheet Details
  credentials_file: str = "credentials.json"
  spreadsheet_name: str = "EMI"
  worksheet_index: int = 1  # 0-indexed: 1 represents the 2nd tab
  data_range: str = "A283:BG437"
  disable_ssl: bool = True

  # Output TSV file paths
  master_tsv_path: str = "emi_records.tsv"
  payment_tsv_path: str = "emi_payments.tsv"

  # Target Destination Worksheets
  loan_spreadsheet: str = "LOAN"
  loan_worksheet: str = "LOAN2026"
  payment_spreadsheet: str = "PAYMENT"
  payment_worksheet: str = "PAYMENT2026"

  # Loan Identifier settings
  start_loan_id: int = 1001

  # Column Boundary Indices (0-based)
  paired_phase_start_col: int = 12  # Column M
  paired_phase_end_col: int = 38  # Up to Column AL (exclusive)
  single_phase_start_col: int = 38  # Column AM
  max_columns: int = 59  # Column BG is index 58

  # Scopes
  scopes: List[str] = field(
      default_factory=lambda: [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive",
      ]
  )
