import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

# Matches a transaction row: DD/MM/YYYY <description> $<valor> $<saldo>
_ROW_RE = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$(-?[\d,]+\.\d{2})\s+\$[\d,]+\.\d{2}\s*$"
)


def _parse_amount(raw: str) -> Decimal:
    """Parse Nequi amount string: remove $ and thousands comma, keep decimal dot."""
    s = raw.strip().lstrip("$").replace(",", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"Cannot parse Nequi amount: {raw!r}")


def parse_nequi_pdf(file_path: Path, password: str | None = None) -> list[dict]:
    """
    Parse a Nequi savings account PDF statement.

    Returns a list of transaction dicts:
        {"posted_at": date, "description": str, "valor": Decimal}

    - valor > 0  => money in (ingreso)
    - valor < 0  => money out (gasto, transferencia)
    """
    transactions = []

    with pdfplumber.open(file_path, password=password or "") as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = _ROW_RE.match(line.strip())
                if not m:
                    continue

                fecha_str, description, valor_str = m.group(1), m.group(2), m.group(3)

                try:
                    posted_at = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                except ValueError:
                    continue

                try:
                    valor = _parse_amount(valor_str)
                except ValueError:
                    continue

                transactions.append({
                    "posted_at": posted_at,
                    "description": description.strip(),
                    "valor": valor,
                })

    if not transactions:
        raise ValueError(f"No transactions found in {file_path.name}")

    return transactions
