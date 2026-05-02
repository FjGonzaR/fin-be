"""
Seed category_examples table with curated examples.

Categories are stored in the `categories` table (managed by admin) — this
script looks them up by slug. Run after migration 014.

Usage:
    source venv/bin/activate
    python scripts/seed_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.category import Category
from app.models.category_example import CategoryExample

# (description_clean, category_slug)
EXAMPLES: list[tuple[str, str]] = [
    ("CUOTA DE MANEJO", "COBRO_BANCARIO"),
    ("DL DIDI RIDES CO", "TRANSPORTE"),
    ("DLO*DIDI", "TRANSPORTE"),
    ("ACTION BLACK VNP", "SALUD"),
    ("COMCEL CAV CALLE 140 B", "HOGAR"),
    ("PARQUEADERO 11 ED HHC", "TRANSPORTE"),
    ("SPOTIFY", "OCIO"),
    ("EXITO WOW COUNTRY", "HOGAR"),
    ("DLO*DIDI FOOD CO PAYIN", "DOMICILIOS"),
    ("OPENAI *CHATGPT SUBSCR", "TRABAJO"),
    ("Priority Pass", "OCIO"),
    ("PAGO FACTURA MOVIL", "HOGAR"),
    ("MIRANDA DISCO BAR Y PE", "OCIO"),
    ("BARU BAR Y GRILL", "OCIO"),
    ("MERCADOPAGO COLOMBIA", "OCIO"),
    ("CURSOR USAGE JAN", "TRABAJO"),
    ("CURSOR, AI POWERED IDE", "TRABAJO"),
    ("OPENROUTER, INC", "EDUCACION"),
    ("APPLE.COM/BILL", "OCIO"),
    ("CLAUDE.AI SUBSCRIPTION", "TRABAJO"),
    ("OPENAI", "TRABAJO"),
    ("PAYPAL *COORDI USA", "OCIO"),
    ("APPARTA - TU MESA", "OCIO"),
    ("AMAZON MKTPL*BS2OE2SZ3", "OCIO"),
    ("UBER RIDES", "TRANSPORTE"),
    ("RAPPI COLOMBIA*DL", "DOMICILIOS"),
    ("CINECITY", "OCIO"),
    ("NETFLIX DL", "OCIO"),
    ("MERCPAGO*TUPINCO", "REGALOS"),
    ("HOMECENTER CEDRITOS", "HOGAR"),
    ("AEROREPUBLICA", "OCIO"),
    ("HELADERIA UNICENTRO", "RESTAURANTES"),
    ("PARMESSANO UNICENTRO", "RESTAURANTES"),
    ("BOLD*padre nuestro", "RESTAURANTES"),
    ("IL FORNO LOS COLORES", "RESTAURANTES"),
    ("FARMATODO COLORES", "SALUD"),
    ("DROG CAFAM SAO PAULO C", "SALUD"),
    ("IPS S S SAO PAULO", "SALUD"),
    ("SABORES NIKKEI", "RESTAURANTES"),
    ("DROGUERIA SAN PAULO", "SALUD"),
    ("TIEN DE CAFE JUAN VALD", "RESTAURANTES"),
    ("DROGUERIA CC EL TESORO", "SALUD"),
    ("CAFE PERGAMINO LAURELE", "RESTAURANTES"),
    ("MAESTRIA DEL FUEGO LAU", "RESTAURANTES"),
    ("FALABELLA", "OCIO"),
    ("STARBUCKS SAN DIEGO", "RESTAURANTES"),
    ("EXITO SAN DIEGO", "HOGAR"),
    ("TJV CC SAN DIEGO 2", "RESTAURANTES"),
    ("GRUPO MURRI SAS", "RESTAURANTES"),
    ("R57 CREPESYWAFFLES TOR", "RESTAURANTES"),
    ("PASTIER CL 140", "RESTAURANTES"),
    ("TIENDA D1 AV 19 CEDROS", "HOGAR"),
    ("BOLD*LONDO", "RESTAURANTES"),
    ("DELIMEX SAS CEDRITOS", "RESTAURANTES"),
    ("ABONO SUCURSAL VIRTUAL", "PAGO"),
]


def seed(db) -> tuple[int, int, int]:
    inserted = 0
    skipped = 0
    missing = 0
    slug_to_id = {c.slug: c.id for c in db.query(Category).all()}
    for description_clean, slug in EXAMPLES:
        cat_id = slug_to_id.get(slug)
        if not cat_id:
            missing += 1
            print(f"  [skip] category '{slug}' not found for '{description_clean}'")
            continue
        exists = (
            db.query(CategoryExample)
            .filter(
                CategoryExample.description_clean == description_clean,
                CategoryExample.category_id == cat_id,
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(CategoryExample(description_clean=description_clean, category_id=cat_id))
        inserted += 1
    db.commit()
    return inserted, skipped, missing


if __name__ == "__main__":
    db = SessionLocal()
    try:
        inserted, skipped, missing = seed(db)
        print(f"Seed complete: {inserted} inserted, {skipped} already existed, {missing} missing categories.")
    finally:
        db.close()
