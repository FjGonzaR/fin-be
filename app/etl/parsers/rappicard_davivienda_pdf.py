import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

# Matches the start of a transaction row: card_type, date, rest
_ROW_START = re.compile(r"^(Virtual|-)\s+(\d{4}-\d{2}-\d{2})\s*(.*)", re.DOTALL)

# Case A: purchase — valor, capital, cuotas, capital_pendiente, tasa_mv, tasa_ea
_TAIL_A = re.compile(
    r"\$([\d.,]+)\s+\$([\d.,]+)\s+(.+?)\s+\$([\d.,]+)\s+([\d.,]+%)\s+([\d.,]+%)$"
)

# Case B: payment — valor, N/A N/A N/A, tasa_mv, tasa_ea
_TAIL_B = re.compile(
    r"\$(-?[\d.,]+)\s+N/A\s+N/A\s+N/A\s+([\d.,]+%)\s+([\d.,]+%)$"
)

# Description fragments appear ~6px above/below their data row; row spacing is ~19px.
_FRAG_THRESHOLD = 9


def _parse_amount(raw: str) -> Decimal:
    """Parse Colombian currency string: strip $, remove . thousands, replace , decimal."""
    s = raw.strip().lstrip("$").replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Cannot parse amount: {raw!r}")


def _parse_tail(tail: str) -> dict | None:
    """Try to parse the numeric tail of a row. Returns field dict or None."""
    m = _TAIL_A.search(tail)
    if m:
        return {
            "valor_transaccion": _parse_amount(m.group(1)),
            "capital_facturado": _parse_amount(m.group(2)),
            "cuotas_raw": m.group(3).strip(),
            "capital_pendiente": _parse_amount(m.group(4)),
            "tasa_mv": m.group(5),
            "tasa_ea": m.group(6),
        }

    m = _TAIL_B.search(tail)
    if m:
        return {
            "valor_transaccion": _parse_amount(m.group(1)),
            "capital_facturado": None,
            "cuotas_raw": None,
            "capital_pendiente": None,
            "tasa_mv": m.group(2),
            "tasa_ea": m.group(3),
        }

    return None


def _extract_rows(file_path: Path) -> list[tuple[int, str]]:
    """
    Extract (global_y, text) rows from all pages using word bounding boxes.

    Each page's y coordinates are offset by page_num * 10_000 to avoid
    collisions across pages.
    """
    all_rows: list[tuple[int, str]] = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            rows_by_y: dict[int, list] = defaultdict(list)
            for w in words:
                global_y = page_num * 10_000 + round(w["top"])
                rows_by_y[global_y].append(w)
            for y in sorted(rows_by_y):
                text = " ".join(
                    w["text"]
                    for w in sorted(rows_by_y[y], key=lambda w: w["x0"])
                )
                all_rows.append((y, text))
    return all_rows


def parse_rappicard_davivienda_pdf(file_path: Path) -> list[dict]:
    """
    Parse a RappiCard/Davivienda PDF bank statement.

    Returns a list of raw transaction dicts with keys:
        card_type, posted_at, description_raw, valor_transaccion,
        capital_facturado, cuotas_raw, capital_pendiente,
        tasa_mv, tasa_ea, currency
    """
    rows = _extract_rows(file_path)

    # Find the "Detalle de transacciones" section
    section_start = None
    for i, (_, text) in enumerate(rows):
        if "Detalle de transacciones" in text:
            section_start = i + 1
            break
    if section_start is None:
        raise ValueError(
            f"Section 'Detalle de transacciones' not found in {file_path.name}"
        )

    section = rows[section_start:]

    # Identify data row indices
    data_indices = [i for i, (_, t) in enumerate(section) if _ROW_START.match(t)]
    if not data_indices:
        return []

    # Assign non-data rows within _FRAG_THRESHOLD of a data row to that row
    frags: dict[int, list[tuple[int, str]]] = defaultdict(list)
    data_index_set = set(data_indices)
    for i, (y, text) in enumerate(section):
        if i in data_index_set or not text.strip():
            continue
        nearest = min(data_indices, key=lambda di: abs(section[di][0] - y))
        if abs(section[nearest][0] - y) <= _FRAG_THRESHOLD:
            frags[nearest].append((y, text))

    # Build transactions
    transactions: list[dict] = []
    for didx in data_indices:
        data_y, data_text = section[didx]
        m = _ROW_START.match(data_text)
        card_type = m.group(1)

        try:
            posted_at = date.fromisoformat(m.group(2))
        except ValueError:
            continue

        inline_rest = m.group(3).strip()

        # Split inline_rest into description + numeric tail at the first $
        dollar_pos = inline_rest.find("$")
        if dollar_pos == -1:
            inline_desc = inline_rest
            tail_text = ""
        else:
            inline_desc = inline_rest[:dollar_pos].strip()
            tail_text = inline_rest[dollar_pos:].strip()

        # Collect description fragments sorted by y
        row_frags = sorted(frags.get(didx, []), key=lambda x: x[0])
        prefix = [t for y, t in row_frags if y < data_y]
        suffix = [t for y, t in row_frags if y > data_y]

        desc_parts = prefix + ([inline_desc] if inline_desc else []) + suffix
        description_raw = " ".join(desc_parts).strip()

        tail_data = _parse_tail(tail_text)
        if tail_data is None:
            continue  # skip unparseable row (e.g. header lines)

        transactions.append(
            {
                "card_type": card_type,
                "posted_at": posted_at,
                "description_raw": description_raw,
                "valor_transaccion": tail_data["valor_transaccion"],
                "capital_facturado": tail_data["capital_facturado"],
                "cuotas_raw": tail_data["cuotas_raw"],
                "capital_pendiente": tail_data["capital_pendiente"],
                "tasa_mv": tail_data["tasa_mv"],
                "tasa_ea": tail_data["tasa_ea"],
                "currency": "COP",
            }
        )

    return transactions
