"""Date cleaning, normalization, and parsing utility."""

from datetime import datetime, timedelta
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class DateParser:
  """Normalizes diverse spreadsheet date inputs into standard MM/DD/YYYY format."""

  DATE_FORMATS = [
      "%d-%B-%Y",
      "%d-%b-%Y",
      "%d-%B-%y",
      "%d-%b-%y",
      "%d %B %Y",
      "%d %b %Y",
      "%d %B %y",
      "%d %b %y",
      "%d/%m/%Y",
      "%d-%m-%Y",
      "%d.%m.%Y",
      "%d/%m/%y",
      "%d-%m-%y",
      "%d.%m.%y",
      "%Y-%m-%d",
      "%Y/%m/%d",
      "%b %d, %Y",
      "%B %d, %Y",
      "%b %d %Y",
      "%m/%d/%Y",
      "%m-%d-%Y",
  ]

  NOISE_KEYWORDS = [
      "bhikhari",
      "bhikari",
      "pkt",
      "p.k.t",
      "cash",
      "online",
      "emi",
      "date",
      "col_",
      "(",
      ")",
  ]

  @classmethod
  def normalize_to_mm_dd_yyyy(cls, raw_val: Optional[str]) -> str:
    """Parses text containing dates or Excel serial numbers into MM/DD/YYYY."""
    if not raw_val or not str(raw_val).strip():
      return ""

    val_str = str(raw_val).strip()

    # 1. Handle Excel/Sheets 5-digit serial numbers
    if val_str.isdigit() and len(val_str) == 5:
      try:
        parsed_dt = datetime(1899, 12, 30) + timedelta(days=int(val_str))
        return parsed_dt.strftime("%m/%d/%Y")
      except Exception as e:
        logger.debug(f"Failed to parse serial date '{val_str}': {e}")

    # 2. Clean noise words
    cleaned_s = val_str.lower()
    for word in cls.NOISE_KEYWORDS:
      cleaned_s = cleaned_s.replace(word, "")
    cleaned_s = re.sub(r"^[_\s\-./:]+|[_\s\-./:]+$", "", cleaned_s).strip()

    # 3. Direct format match
    for fmt in cls.DATE_FORMATS:
      try:
        dt = datetime.strptime(cleaned_s, fmt)
        if dt.year < 100:
          dt = dt.replace(year=dt.year + 2000)
        return dt.strftime("%m/%d/%Y")
      except ValueError:
        continue

    # 4. Regex extraction fallback
    match = re.search(r"(\d{1,2}[/\-.\s][a-zA-Z]{3,9}[/\-.\s]\d{2,4})", val_str)
    if not match:
      match = re.search(r"(\d{1,2}[/\-.\s]\d{1,2}[/\-.\s]\d{2,4})", val_str)

    if match:
      candidate = match.group(1).strip()
      for fmt in cls.DATE_FORMATS:
        try:
          dt = datetime.strptime(candidate, fmt)
          if dt.year < 100:
            dt = dt.replace(year=dt.year + 2000)
          return dt.strftime("%m/%d/%Y")
        except ValueError:
          continue

    return val_str
