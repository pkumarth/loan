"""Data Transfer Objects representing Master Loan records and Payment transactions."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class LoanRecord:
  loan_number: str
  borrower_name: str
  guardian_name: str
  mohalla: str
  mobile: str
  principal_amt_in_words: str
  principal_amt: str
  loan_disbursement_date: str
  loan_first_due_date: str
  loan_maturity_date: str
  total_installment: str
  installment_amount: str

  def to_tsv_row(self) -> List[str]:
    return [
        self.loan_number,
        self.borrower_name,
        self.guardian_name,
        self.mohalla,
        self.mobile,
        self.principal_amt_in_words,
        self.principal_amt,
        self.loan_disbursement_date,
        self.loan_first_due_date,
        self.loan_maturity_date,
        self.total_installment,
        self.installment_amount,
    ]


@dataclass
class PaymentRecord:
  payment_id: str
  loan_number: str
  borrower_name: str
  guardian_name: str
  mohalla: str
  mobile: str
  principal_amt_in_words: str
  principal_amt: str
  loan_disbursement_date: str
  loan_first_due_date: str
  loan_maturity_date: str
  total_installment: str
  installment_amount: str
  payment_date: str
  payment_mode: str
  paid_to_pkt: str
  paid_to_bhikhari: str
  raw_cell_value: str

  def to_tsv_row(self) -> List[str]:
    return [
        self.payment_id,
        self.loan_number,
        self.borrower_name,
        self.guardian_name,
        self.mohalla,
        self.mobile,
        self.principal_amt_in_words,
        self.principal_amt,
        self.loan_disbursement_date,
        self.loan_first_due_date,
        self.loan_maturity_date,
        self.total_installment,
        self.installment_amount,
        self.payment_date,
        self.payment_mode,
        self.paid_to_pkt,
        self.paid_to_bhikhari,
        self.raw_cell_value,
    ]
