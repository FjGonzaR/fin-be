"""
Standalone test script for the RappiCard/Davivienda PDF parser.
Usage:
    python scripts/test_rappicard_parser.py data/uploads/rappi-0226.pdf
"""
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.etl.parsers.rappicard_davivienda_pdf import parse_rappicard_davivienda_pdf


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_rappicard_parser.py data/uploads/rappi-0226.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    rows = parse_rappicard_davivienda_pdf(pdf_path)
    print(f"Parsed {len(rows)} transactions")

    if rows:
        print("\nFirst row:")
        for k, v in rows[0].items():
            print(f"  {k}: {v!r}")

        if len(rows) > 1:
            print("\nLast row:")
            for k, v in rows[-1].items():
                print(f"  {k}: {v!r}")

    # Verify sign conventions
    errors = []
    for i, row in enumerate(rows):
        v = row["valor_transaccion"]
        cuotas = row["cuotas_raw"]
        capital = row["capital_facturado"]

        if capital is not None:
            # Purchase: valor_transaccion should be positive (expense)
            if v <= 0:
                errors.append(
                    f"Row {i}: purchase has non-positive valor_transaccion={v}"
                )
        else:
            # Payment: valor_transaccion should be negative (credit)
            if v >= 0:
                errors.append(
                    f"Row {i}: payment has non-negative valor_transaccion={v}"
                )

    if errors:
        print("\nVerification FAILED:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nVerification PASSED: sign conventions look correct.")


if __name__ == "__main__":
    main()
