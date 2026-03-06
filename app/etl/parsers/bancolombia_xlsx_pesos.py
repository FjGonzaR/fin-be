from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd


HEADER_COLUMNS = [
    "Número de autorización",
    "Fecha",
    "Movimientos",
    "Valor Movimiento",
    "Número de cuotas",
    "Valor cuota/abono",
    "Interés mensual (%)",
    "Interés anual (%)",
    "Saldo pendiente",
]


def parse_colombian_number(value: str) -> Decimal | None:
    """
    Parse Colombian number format:
    - thousands separator: '.'
    - decimal separator: ','
    - optional leading '-'

    Returns Decimal or None if unparseable.
    """
    if pd.isna(value) or value is None or str(value).strip() == "":
        return None

    try:
        # Convert to string and strip
        s = str(value).strip()

        # Remove thousands separator (.)
        s = s.replace(".", "")

        # Replace decimal separator (,) with (.)
        s = s.replace(",", ".")

        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def parse_date_ddmmyyyy(value: str) -> datetime | None:
    """Parse date in dd/mm/yyyy format."""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return None

    try:
        return datetime.strptime(str(value).strip(), "%d/%m/%Y")
    except ValueError:
        return None


def is_empty_row(row_values: list) -> bool:
    """Check if a row is completely empty."""
    return all(pd.isna(val) or str(val).strip() == "" for val in row_values)


def is_header_row(row_values: list) -> bool:
    """Check if first 9 columns match expected header."""
    if len(row_values) < 9:
        return False

    for i, expected in enumerate(HEADER_COLUMNS):
        actual = str(row_values[i]).strip() if not pd.isna(row_values[i]) else ""
        if actual != expected:
            return False

    return True


def is_end_marker(row_values: list) -> bool:
    """Check if row is the 'Movimientos durante el periodo' marker."""
    if len(row_values) < 1:
        return False

    first_col = str(row_values[0]).strip() if not pd.isna(row_values[0]) else ""
    return first_col == "Movimientos durante el periodo"


_SHEET_CURRENCY: dict[str, str] = {
    "PESOS": "COP",
    "DOLARES": "USD",
}


def _detect_currency(rows: list[list]) -> str:
    """Read 'Moneda:' row from sheet metadata (first 15 rows)."""
    for row in rows[:15]:
        first = str(row[0]).strip() if not pd.isna(row[0]) else ""
        second = str(row[1]).strip() if len(row) > 1 and not pd.isna(row[1]) else ""
        if first == "Moneda:":
            val = second.upper()
            if "PESOS" in val:
                return "COP"
            if "DOLAR" in val:
                return "USD"
    return "COP"


def _parse_sheet_rows(rows: list[list], currency: str) -> list[dict]:
    """Parse all transaction blocks from a sheet's raw row list."""
    header_indices = [i for i, row in enumerate(rows) if is_header_row(row)]

    if not header_indices:
        return []

    parsed_transactions = []

    for header_idx in header_indices:
        i = header_idx + 1
        empty_count = 0
        current_tx = None

        while i < len(rows):
            row = rows[i]

            if is_header_row(row):
                break
            if is_end_marker(row):
                break

            if is_empty_row(row):
                empty_count += 1
                if empty_count >= 3:
                    break
                i += 1
                continue
            else:
                empty_count = 0

            while len(row) < 9:
                row.append(None)

            auth = row[0]
            fecha = row[1]
            movimientos = row[2]
            valor_movimiento = row[3]
            num_cuotas = row[4]
            valor_cuota = row[5]
            interes_mensual = row[6]
            interes_anual = row[7]
            saldo_pendiente = row[8]

            auth_str = str(auth).strip() if not pd.isna(auth) else ""
            fecha_str = str(fecha).strip() if not pd.isna(fecha) else ""
            movimientos_str = str(movimientos).strip() if not pd.isna(movimientos) else ""

            parsed_date = parse_date_ddmmyyyy(fecha_str)
            parsed_valor = parse_colombian_number(str(valor_movimiento))

            if auth_str and parsed_date and movimientos_str and parsed_valor is not None:
                if current_tx:
                    parsed_transactions.append(current_tx)

                current_tx = {
                    "auth_number": auth_str,
                    "posted_at": parsed_date.date(),
                    "movimientos": movimientos_str,
                    "valor_movimiento": parsed_valor,
                    "cuotas_raw": str(num_cuotas).strip() if not pd.isna(num_cuotas) else None,
                    "valor_cuota": parse_colombian_number(str(valor_cuota)),
                    "interes_mensual": parse_colombian_number(str(interes_mensual)),
                    "interes_anual": parse_colombian_number(str(interes_anual)),
                    "saldo_pendiente": parse_colombian_number(str(saldo_pendiente)),
                    "extra_details": [],
                    "currency": currency,
                }
            elif current_tx and not auth_str and not fecha_str and movimientos_str:
                current_tx["extra_details"].append(movimientos_str)

            i += 1

        if current_tx:
            parsed_transactions.append(current_tx)

    return parsed_transactions


def parse_bancolombia_xlsx(file_path: Path) -> list[dict]:
    """
    Parse all PESOS and DOLARES sheets from a Bancolombia XLSX file.
    Each transaction dict includes a 'currency' field (COP or USD).
    """
    xl = pd.ExcelFile(file_path)
    all_transactions = []

    for sheet_name in xl.sheet_names:
        if sheet_name.upper() not in _SHEET_CURRENCY:
            continue
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        rows = df.values.tolist()
        currency = _detect_currency(rows)
        txs = _parse_sheet_rows(rows, currency)
        all_transactions.extend(txs)

    if not all_transactions:
        raise ValueError(f"No transactions found in PESOS or DOLARES sheets of {file_path.name}")

    return all_transactions


# Backward-compatible alias
def parse_bancolombia_xlsx_pesos(file_path: Path) -> list[dict]:
    return parse_bancolombia_xlsx(file_path)
