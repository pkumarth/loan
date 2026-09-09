"""Interactive terminal runtime execution tool to search your cloud database sheets by ID."""

import json
import logging
from config import SheetConfig
from sheet_client import GoogleSheetClient
from search_service import LoanSearchService

# Setup minimalist presentation logging layout
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    config = SheetConfig()

    # Authorize client using our corporate proxy verification bypass engine
    client = GoogleSheetClient(config)
    searcher = LoanSearchService(client)

    print("\n" + "="*50)
    print("      LIVE GOOGLE SHEETS LOAN LOOKUP SYSTEM      ")
    print("="*50)

    # Prompt the operator for input
    user_query = input("👉 Enter Loan ID to search (e.g. 1001): ").strip()

    if not user_query:
        print("❌ Search query cannot be blank.")
        return

    # Execute search
    result = searcher.search_by_loan_id(user_query)

    if result:
        print(f"\n✅ SUCCESS: Found profile data for Record {user_query}")
        print("\n📝 --- LOAN MASTER METADATA ---")
        print(json.dumps(result["loan_metadata"], indent=4, ensure_ascii=False))

        print(f"\n📊 --- TRANSACTION HISTORY ({result['total_payments_count']} Records) [Sorted by Date] ---")
        if result["total_payments_count"] == 0:
            print("   (No past collections recorded for this customer account)")
        else:
            for idx, pay in enumerate(result["payments"], start=1):
                # Safely convert payment numeric values to strings before applying alignment padding
                pkt_val = str(pay.get('paid_to_pkt', ''))
                bhikhari_val = str(pay.get('paid_to_bhikhari', ''))
                mode_val = str(pay.get('payment_mode', ''))

                print(
                    f"   [{idx}] Date: {pay.get('payment_date')} | "
                    f"Mode: {mode_val:8s} | "
                    f"Paid PKT: {pkt_val:5s} | "
                    f"Paid Bhikhari: {bhikhari_val:5s} | "
                    f"Txn ID: {pay.get('payment_id')}"
                )
        print("="*60 + "\n")
    else:
        print(f"\n❌ Error: Could not locate a matching transaction block for ID '{user_query}'.")


if __name__ == "__main__":
    main()
