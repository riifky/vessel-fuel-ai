
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import pickle

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

BASE_DIR = Path(__file__).parent
CLIENT_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.pickle"


def get_sheet():
    creds = None

    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    client = gspread.authorize(creds)
    spreadsheet_id = "1ilDSsPG3_mlSTfxhHke6aUAPzoFxM-sv-upqwhPF-eQ"
    spreadsheet = client.open_by_key(spreadsheet_id)

    return spreadsheet.sheet1
