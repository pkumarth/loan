"""Extracts, transforms, and unpivots Google Sheets loan and payment records."""

from itertools import zip_longest
import logging
from typing import List, Tuple
from config import SheetConfig
from models import LoanRecord, PaymentRecord
from utils.date_parser import DateParser

logger = logging.getLogger(__name__)


class LoanDataProcessor:

  def __init__(self, config: SheetConfig):
    self.config = config

  def _deduplicate_headers(self, raw_headers: List[str]) -> List[str]:
    """Appends index suffixes to duplicate header titles (e.g. 'मूल धन_1')."""
    seen = {}
    unique_headers = []
    for h in raw_headers:
      name = h.strip()
      if name in seen:
        seen[name] += 1
        unique_headers.append(f"{name}_{seen[name]}")
      else:
        seen[name] = 0
        unique_headers.append(name)
    return unique_headers

  @staticmethod
  def _is_valid_payment(val: str) -> bool:
    v = str(val).strip()
    return bool(v and v not in ("-", "0", "0.0", "None"))

  @staticmethod
  def _determine_payment_mode(paid_pkt: str, paid_bhikhari: str) -> str:
    if paid_pkt and paid_bhikhari:
      return "split"
    if paid_pkt:
      return "online"
    if paid_bhikhari:
      return "cash"
    return ""

  def process(
      self, raw_data: List[List[str]]
  ) -> Tuple[List[LoanRecord], List[PaymentRecord]]:
    """Transforms raw 2D sheet data into Master Loan Records and Payment Transactions."""
    raw_headers = raw_data[0]
    data_rows = raw_data[1:]
    unique_headers = self._deduplicate_headers(raw_headers)

    master_loans: List[LoanRecord] = []
    payment_transactions: List[PaymentRecord] = []

    for row in data_rows:
      if not row or not any(row):
        continue

      # 1. Generate 6-digit zero-padded Loan ID
      loan_id = f"{self.config.start_loan_id + len(master_loans):06d}"
      row_dict = dict(zip_longest(unique_headers, row, fillvalue=""))

      # 2. Extract & Normalize Master Loan Record
      loan = LoanRecord(
          loan_number=loan_id,
          borrower_name=row_dict.get("उधारकर्ता का नाम", "").strip(),
          guardian_name=row_dict.get("अभिभावक", "").strip(),
          mohalla=row_dict.get("मोहल्ला", "").strip(),
          mobile=row_dict.get("मोबाइल नंबर", "").strip(),
          principal_amt_in_words=row_dict.get("मूल धन", "").strip(),
          principal_amt=row_dict.get("मूल धन_1", "").strip(),
          loan_disbursement_date=DateParser.normalize_to_mm_dd_yyyy(
              row_dict.get("ऋण तिथि", "")
          ),
          loan_first_due_date=DateParser.normalize_to_mm_dd_yyyy(
              row_dict.get("पहली भुगतान तिथि", "")
          ),
          loan_maturity_date=DateParser.normalize_to_mm_dd_yyyy(
              row_dict.get("अंतिम भुगतान तिथि", "")
          ),
          total_installment=row_dict.get("कुल किस्त", "0").strip(),
          installment_amount=row_dict.get("किस्त राशि", "").strip(),
      )
      master_loans.append(loan)

      payment_seq = 1

      # 3. Phase 1: Paired Columns (M to AL -> Bhikhari, PKT)
      paired_limit = min(len(row), self.config.paired_phase_end_col)
      for col_idx in range(
          self.config.paired_phase_start_col, paired_limit, 2
      ):
        val_bhikhari = str(row[col_idx]).strip() if col_idx < len(row) else ""
        val_pkt = (
            str(row[col_idx + 1]).strip() if (col_idx + 1) < len(row) else ""
        )

        paid_bhikhari = (
            val_bhikhari if self._is_valid_payment(val_bhikhari) else ""
        )
        paid_pkt = val_pkt if self._is_valid_payment(val_pkt) else ""

        if paid_bhikhari or paid_pkt:
          payment_id = f"{payment_seq:06d}_{loan.loan_number}"
          payment_seq += 1

          header_m = (
              raw_headers[col_idx].strip()
              if col_idx < len(raw_headers)
              else ""
          )
          header_n = (
              raw_headers[col_idx + 1].strip()
              if (col_idx + 1) < len(raw_headers)
              else ""
          )
          raw_date = header_m or header_n or f"Col_{col_idx+1}"
          payment_date = DateParser.normalize_to_mm_dd_yyyy(raw_date)

          payment_transactions.append(
              PaymentRecord(
                  payment_id=payment_id,
                  loan_number=loan.loan_number,
                  borrower_name=loan.borrower_name,
                  guardian_name=loan.guardian_name,
                  mohalla=loan.mohalla,
                  mobile=loan.mobile,
                  principal_amt_in_words=loan.principal_amt_in_words,
                  principal_amt=loan.principal_amt,
                  loan_disbursement_date=loan.loan_disbursement_date,
                  loan_first_due_date=loan.loan_first_due_date,
                  loan_maturity_date=loan.loan_maturity_date,
                  total_installment=loan.total_installment,
                  installment_amount=loan.installment_amount,
                  payment_date=payment_date,
                  payment_mode=self._determine_payment_mode(
                      paid_pkt, paid_bhikhari
                  ),
                  paid_to_pkt=paid_pkt,
                  paid_to_bhikhari=paid_bhikhari,
                  raw_cell_value=(
                      f"Bhikhari: {val_bhikhari} | PKT: {val_pkt}".strip(" |")
                  ),
              )
          )

      # 4. Phase 2: Single Columns (AM to BG -> PKT only)
      total_cols = min(len(row), self.config.max_columns)
      for col_idx in range(self.config.single_phase_start_col, total_cols):
        cell_val = str(row[col_idx]).strip()

        if self._is_valid_payment(cell_val):
          payment_id = f"{payment_seq:06d}_{loan.loan_number}"
          payment_seq += 1

          raw_date = (
              raw_headers[col_idx].strip()
              if col_idx < len(raw_headers)
              else f"Col_{col_idx+1}"
          )
          payment_date = DateParser.normalize_to_mm_dd_yyyy(raw_date)

          payment_transactions.append(
              PaymentRecord(
                  payment_id=payment_id,
                  loan_number=loan.loan_number,
                  borrower_name=loan.borrower_name,
                  guardian_name=loan.guardian_name,
                  mohalla=loan.mohalla,
                  mobile=loan.mobile,
                  principal_amt_in_words=loan.principal_amt_in_words,
                  principal_amt=loan.principal_amt,
                  loan_disbursement_date=loan.loan_disbursement_date,
                  loan_first_due_date=loan.loan_first_due_date,
                  loan_maturity_date=loan.loan_maturity_date,
                  total_installment=loan.total_installment,
                  installment_amount=loan.installment_amount,
                  payment_date=payment_date,
                  payment_mode="online",
                  paid_to_pkt=cell_val,
                  paid_to_bhikhari="",
                  raw_cell_value=cell_val,
              )
          )

    return master_loans, payment_transactions
