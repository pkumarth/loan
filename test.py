from google.oauth2.service_account import Credentials
import gspread

# 1. Define the permissions scope required for Google Sheets and Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# 2. Load your service account credentials
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

# 3. Authorize the client
client = gspread.authorize(creds)

# 4. Open the spreadsheet by name or URL
# Replace 'Your Spreadsheet Name' with the exact name of your sheet
spreadsheet = client.open("EMI")

# 5. Select the worksheet (tab) by name or index
worksheet = spreadsheet.get_worksheet(1)  # Or use spreadsheet.get_worksheet(0)

# 6. Read the data
# Get all records as a list of dictionaries (rows use the header as keys)
data_as_dicts = worksheet.get_all_records()

# Alternatively, get all values as a simple list of lists (rows and columns)
# all_values = worksheet.get_all_values()

# Print the results
print(data_as_dicts)
