"""
Writes collected rows to Google Sheets - separate tab per platform.
"""
import logging
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Timestamp", "Collected At", "Person/Handle", "Platform",
    "Type", "Matched Keyword", "Content Snippet", "URL",
]

TYPE_OPTIONS = ["Post", "Comment", "Reddit Thread", "Customer Review"]


class SheetsWriter:
    def __init__(self, service_account_file, sheet_id):
        creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(sheet_id)

    def _get_or_create_worksheet(self, name):
        try:
            ws = self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
            self._apply_type_dropdown(ws)
            logger.info(f"Created new worksheet tab '{name}' with headers + dropdown")
        return ws

    def _apply_type_dropdown(self, worksheet):
        type_col_index = HEADERS.index("Type") + 1
        rule = {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in TYPE_OPTIONS]},
            "showCustomUi": True, "strict": True,
        }
        body = {"requests": [{"setDataValidation": {
            "range": {"sheetId": worksheet.id, "startRowIndex": 1,
                       "startColumnIndex": type_col_index - 1, "endColumnIndex": type_col_index},
            "rule": rule,
        }}]}
        self.spreadsheet.batch_update(body)

    def _existing_urls(self, worksheet):
        url_col_index = HEADERS.index("URL") + 1
        values = worksheet.col_values(url_col_index)
        return set(values[1:])

    def write_rows(self, rows, worksheet_name, collected_at_iso):
        if not rows:
            return 0
        worksheet = self._get_or_create_worksheet(worksheet_name)
        existing = self._existing_urls(worksheet)
        new_rows = [r for r in rows if r["url"] not in existing]
        if not new_rows:
            logger.info(f"[{worksheet_name}] No new rows to write (all duplicates)")
            return 0

        values = [[r["timestamp"], collected_at_iso, r["author"], r["platform"],
                    r["type"], r["matched_keyword"], r["content_snippet"], r["url"]]
                   for r in new_rows]

        worksheet.append_rows(values, value_input_option="USER_ENTERED")
        logger.info(f"[{worksheet_name}] Wrote {len(new_rows)} new rows ({len(rows) - len(new_rows)} duplicates skipped)")
        return len(new_rows)
