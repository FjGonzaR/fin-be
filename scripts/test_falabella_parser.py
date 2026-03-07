"""
Standalone test script for the Banco Falabella XLSX parser.

Usage:
    python scripts/test_falabella_parser.py /path/to/movimientos-facturados.xlsx

Tests:
    - Colombian currency parsing
    - Correct canonical sign conversion (PAGO/ABONO → positive, expenses → negative)
    - Normal purchase row parsing
    - Payment row parsing
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.etl.normalization import normalize_falabella_transaction
from app.etl.parsers.falabella_xlsx_movimientos import parse_colombian_amount, parse_falabella_xlsx


# ─── Unit tests for Colombian number parsing ──────────────────────────────────

def test_colombian_amount_parsing():
    cases = [
        ("$ 31.990,00",     Decimal("31990.00")),
        ("$ 427.818,65",    Decimal("427818.65")),
        ("$ 1.239.500,00",  Decimal("1239500.00")),
        ("31.990,00",       Decimal("31990.00")),
        ("100,00",          Decimal("100.00")),
        ("0,00",            Decimal("0.00")),
    ]
    errors = []
    for raw, expected in cases:
        result = parse_colombian_amount(raw)
        if result != expected:
            errors.append(f"  parse_colombian_amount({raw!r}) = {result!r}, expected {expected!r}")

    if errors:
        print("FAILED — Colombian amount parsing:")
        for e in errors:
            print(e)
        return False

    print(f"PASSED — Colombian amount parsing ({len(cases)} cases)")
    return True


# ─── Unit tests for sign conversion via normalizer ────────────────────────────

def test_sign_conversion():
    cases = [
        # (description_raw, source_amount, expected_canonical_amount)
        ("COBRO CUOTA MANEJO",           Decimal("31990.00"),    Decimal("-31990.00")),
        ("PAGO TARJETA CMR",             Decimal("427818.65"),   Decimal("427818.65")),
        ("COMPRA HOMECENTER CEDRITOS",   Decimal("1239500.00"),  Decimal("-1239500.00")),
        ("ABONO PAGO ONLINE",            Decimal("50000.00"),    Decimal("50000.00")),
        ("COMPRA SUPERMERCADO",          Decimal("85000.00"),    Decimal("-85000.00")),
    ]
    errors = []
    for desc, source_amt, expected in cases:
        raw = {
            "posted_at": None,
            "description_raw": desc,
            "holder_type": None,
            "source_amount": source_amt,
            "installments_raw": None,
            "installment_value": None,
        }
        result = normalize_falabella_transaction(raw)
        if result["amount"] != expected:
            errors.append(
                f"  '{desc}' source={source_amt} => {result['amount']!r}, expected {expected!r}"
            )

    if errors:
        print("FAILED — sign conversion:")
        for e in errors:
            print(e)
        return False

    print(f"PASSED — sign conversion ({len(cases)} cases)")
    return True


# ─── File parsing ─────────────────────────────────────────────────────────────

def test_file_parsing(file_path: Path) -> bool:
    print(f"\nParsing: {file_path.name}")
    rows = parse_falabella_xlsx(file_path)
    print(f"Parsed {len(rows)} transactions")

    print("\nFirst row:")
    for k, v in rows[0].items():
        print(f"  {k}: {v!r}")

    if len(rows) > 1:
        print("\nLast row:")
        for k, v in rows[-1].items():
            print(f"  {k}: {v!r}")

    # Verify all required fields are present and non-None where expected
    errors = []
    for i, row in enumerate(rows):
        if row["posted_at"] is None:
            errors.append(f"  Row {i}: posted_at is None")
        if not row["description_raw"]:
            errors.append(f"  Row {i}: description_raw is empty")
        if row["source_amount"] is None:
            errors.append(f"  Row {i}: source_amount is None")
        if row["source_amount"] is not None and row["source_amount"] < 0:
            errors.append(
                f"  Row {i}: source_amount is negative ({row['source_amount']}) "
                f"— sign should come from description, not raw amount"
            )

    # Verify normalized sign convention
    for i, row in enumerate(rows):
        normalized = normalize_falabella_transaction(row)
        desc_upper = row["description_raw"].upper()
        is_payment = "PAGO" in desc_upper or "ABONO" in desc_upper
        if is_payment and normalized["amount"] < 0:
            errors.append(
                f"  Row {i}: '{row['description_raw']}' should be POSITIVE "
                f"but got {normalized['amount']}"
            )
        if not is_payment and normalized["amount"] > 0:
            errors.append(
                f"  Row {i}: '{row['description_raw']}' should be NEGATIVE "
                f"but got {normalized['amount']}"
            )

    payments = [r for r in rows if "PAGO" in r["description_raw"].upper() or "ABONO" in r["description_raw"].upper()]
    expenses = [r for r in rows if r not in payments]
    print(f"\nPayments/credits: {len(payments)}")
    print(f"Expenses:         {len(expenses)}")

    if errors:
        print("\nVerification FAILED:")
        for e in errors:
            print(e)
        return False

    print("\nVerification PASSED: all rows parsed and sign conventions are correct.")
    return True


def main():
    print("=" * 60)
    print("Banco Falabella parser tests")
    print("=" * 60)

    results = [
        test_colombian_amount_parsing(),
        test_sign_conversion(),
    ]

    if len(sys.argv) >= 2:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            print(f"\nFile not found: {file_path}")
            sys.exit(1)
        results.append(test_file_parsing(file_path))
    else:
        print("\n(No file provided — skipping file parsing test)")
        print("Usage: python scripts/test_falabella_parser.py /path/to/movimientos.xlsx")

    print("\n" + "=" * 60)
    if all(results):
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
