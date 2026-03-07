from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

SHEET_NAME = "Ultimos Movimientos"

EXPECTED_COLUMNS = [
    "Fecha de Compra",
    "Descripción (*)",
    "Titular/Adicional",
    "Monto Transacción",
    "Cuotas",
    "Valor Cuota",
]

PAYMENT_KEYWORDS = ("PAGO", "ABONO")


def parse_colombian_amount(value) -> Decimal | None:
    """
    Parse Colombian currency format into Decimal.

    Examples:
        "$ 31.990,00"      -> Decimal("31990.00")
        "$ 427.818,65"     -> Decimal("427818.65")
        "$ 1.239.500,00"   -> Decimal("1239500.00")
    """
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None

    # Already numeric (pandas may read unformatted cells as number)
    if isinstance(value, (int, float, Decimal)) and not pd.isna(value):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None

    # Strip currency symbol and whitespace variants (including non-breaking space \xa0)
    s = s.replace("$", "").replace("\xa0", "").replace(" ", "").strip()
    if not s:
        return None

    negative = s.startswith("-")
    if negative:
        s = s[1:]

    # Colombian format: '.' = thousands separator, ',' = decimal separator
    s = s.replace(".", "").replace(",", ".")

    try:
        result = Decimal(s)
        return -result if negative else result
    except InvalidOperation:
        return None


def parse_date(value) -> date | None:
    """Parse a date from pandas cell value (Timestamp, datetime, or string)."""
    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


def _normalize_installments(value) -> str | None:
    """Convert cuotas cell (int, float, or string) to a clean string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip() or None


def parse_falabella_xlsx(file_path: Path) -> list[dict]:
    """
    Parse the 'Ultimos Movimientos' sheet from a Banco Falabella XLSX file.

    Returns a list of raw row dicts with keys:
        posted_at, description_raw, holder_type,
        source_amount, installments_raw, installment_value
    """
    xl = pd.ExcelFile(file_path)
    if SHEET_NAME not in xl.sheet_names:
        raise ValueError(
            f"Sheet '{SHEET_NAME}' not found in {file_path.name}. "
            f"Available sheets: {xl.sheet_names}"
        )

    df = pd.read_excel(file_path, sheet_name=SHEET_NAME, header=0)

    # Strip column names to guard against leading/trailing whitespace in the file
    df.columns = [str(c).strip() for c in df.columns]

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing expected columns in '{SHEET_NAME}': {missing}. "
            f"Found: {list(df.columns)}"
        )

    # Drop fully empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    transactions = []

    for _, row in df.iterrows():
        posted_at = parse_date(row["Fecha de Compra"])
        if posted_at is None:
            continue

        descripcion = row["Descripción (*)"]
        if pd.isna(descripcion):
            continue
        description_raw = str(descripcion).strip()
        if not description_raw:
            continue

        source_amount = parse_colombian_amount(row["Monto Transacción"])
        if source_amount is None:
            continue

        titular = row["Titular/Adicional"]
        holder_type = str(titular).strip() if pd.notna(titular) else None

        installments_raw = _normalize_installments(row["Cuotas"])
        installment_value = parse_colombian_amount(row["Valor Cuota"])

        transactions.append({
            "posted_at": posted_at,
            "description_raw": description_raw,
            "holder_type": holder_type,
            "source_amount": source_amount,
            "installments_raw": installments_raw,
            "installment_value": installment_value,
        })

    if not transactions:
        raise ValueError(
            f"No transactions parsed from '{SHEET_NAME}' in {file_path.name}"
        )

    return transactions
