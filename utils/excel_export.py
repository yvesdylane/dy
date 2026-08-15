from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

COLUMNS = [
    ("name", "Name"),
    ("surname", "Surname"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("gender", "Gender"),
    ("department", "Department"),
    ("group", "Group"),
    ("school", "School"),
    ("dob", "DOB"),
    ("quarter", "Quarter"),
    ("fees_paid", "Fees Paid"),
    ("total_fees", "Total Fees"),
    ("is_active", "Active"),
    ("created_at", "Created At"),
]

SHEET_NAME = "Interns"


def build_excel(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append([label for _, label in COLUMNS])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append([row.get(key) for key, _ in COLUMNS])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
