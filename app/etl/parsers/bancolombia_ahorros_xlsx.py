from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

EXPECTED_HEADERS = ["Fecha", "Descripción", "Referencia", "Valor"]


def _parse_valor(value) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def parse_bancolombia_ahorros_xlsx(file_path: Path) -> list[dict]:
    """
    Parse a Bancolombia savings account (cuenta de ahorros) XLSX file.

    Expected columns: Fecha | Descripción | Referencia | Valor
    - Positive Valor = money in (ingreso)
    - Negative Valor = money out (gasto, pago, inversión)
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"Empty file: {file_path.name}")

    # Find header row
    header_idx = None
    for i, row in enumerate(rows):
        row_vals = [str(c).strip() if c is not None else "" for c in row[:4]]
        if row_vals == EXPECTED_HEADERS:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            f"Could not find header row {EXPECTED_HEADERS} in {file_path.name}"
        )

    transactions = []
    for row in rows[header_idx + 1:]:
        if len(row) < 4:
            continue

        fecha_raw, descripcion, referencia, valor_raw = row[0], row[1], row[2], row[3]

        posted_at = _parse_date(fecha_raw)
        valor = _parse_valor(valor_raw)

        if posted_at is None or valor is None or not descripcion:
            continue

        ref = str(referencia).strip() if referencia and str(referencia).strip() not in ("", "null", "None") else None

        transactions.append({
            "posted_at": posted_at,
            "description": str(descripcion).strip(),
            "reference": ref,
            "valor": valor,
        })

    if not transactions:
        raise ValueError(f"No transactions found in {file_path.name}")

    return transactions
