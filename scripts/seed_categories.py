"""
Seed category_examples table with curated examples.

Usage:
    source venv/bin/activate
    python scripts/seed_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.category_example import CategoryExample
from app.models.enums import Category

EXAMPLES: list[tuple[str, Category]] = [
    ("CUOTA DE MANEJO", Category.COBRO_BANCARIO),
    ("DL DIDI RIDES CO", Category.TRANSPORTE),
    ("DLO*DIDI", Category.TRANSPORTE),
    ("ACTION BLACK VNP", Category.SALUD),
    ("COMCEL CAV CALLE 140 B", Category.HOGAR),
    ("PARQUEADERO 11 ED HHC", Category.TRANSPORTE),
    ("SPOTIFY", Category.OCIO),
    ("EXITO WOW COUNTRY", Category.HOGAR),
    ("DLO*DIDI FOOD CO PAYIN", Category.DOMICILIOS),
    ("OPENAI *CHATGPT SUBSCR", Category.TRABAJO),
    ("Priority Pass", Category.OCIO),
    ("PAGO FACTURA MOVIL", Category.HOGAR),
    ("MIRANDA DISCO BAR Y PE", Category.OCIO),
    ("BARU BAR Y GRILL", Category.OCIO),
    ("MERCADOPAGO COLOMBIA", Category.OCIO),
    ("CURSOR USAGE JAN", Category.TRABAJO),
    ("CURSOR, AI POWERED IDE", Category.TRABAJO),
    ("OPENROUTER, INC", Category.EDUCACION),
    ("APPLE.COM/BILL", Category.OCIO),
    ("CLAUDE.AI SUBSCRIPTION", Category.TRABAJO),
    ("OPENAI", Category.TRABAJO),
    ("PAYPAL *COORDI USA", Category.OCIO),
    ("APPARTA - TU MESA", Category.OCIO),
    ("AMAZON MKTPL*BS2OE2SZ3", Category.OCIO),
    ("UBER RIDES", Category.TRANSPORTE),
    ("RAPPI COLOMBIA*DL", Category.DOMICILIOS),
    ("CINECITY", Category.OCIO),
    ("NETFLIX DL", Category.OCIO),
    ("MERCPAGO*TUPINCO", Category.REGALOS),
    ("HOMECENTER CEDRITOS", Category.HOGAR),
    ("AEROREPUBLICA", Category.OCIO),
    ("HELADERIA UNICENTRO", Category.RESTAURANTES),
    ("PARMESSANO UNICENTRO", Category.RESTAURANTES),
    ("BOLD*padre nuestro", Category.RESTAURANTES),
    ("IL FORNO LOS COLORES", Category.RESTAURANTES),
    ("FARMATODO COLORES", Category.SALUD),
    ("DROG CAFAM SAO PAULO C", Category.SALUD),
    ("IPS S S SAO PAULO", Category.SALUD),
    ("SABORES NIKKEI", Category.RESTAURANTES),
    ("DROGUERIA SAN PAULO", Category.SALUD),
    ("TIEN DE CAFE JUAN VALD", Category.RESTAURANTES),
    ("DROGUERIA CC EL TESORO", Category.SALUD),
    ("CAFE PERGAMINO LAURELE", Category.RESTAURANTES),
    ("MAESTRIA DEL FUEGO LAU", Category.RESTAURANTES),
    ("FALABELLA", Category.OCIO),
    ("STARBUCKS SAN DIEGO", Category.RESTAURANTES),
    ("EXITO SAN DIEGO", Category.HOGAR),
    ("TJV CC SAN DIEGO 2", Category.RESTAURANTES),
    ("GRUPO MURRI SAS", Category.RESTAURANTES),
    ("R57 CREPESYWAFFLES TOR", Category.RESTAURANTES),
    ("PASTIER CL 140", Category.RESTAURANTES),
    ("TIENDA D1 AV 19 CEDROS", Category.HOGAR),
    ("BOLD*LONDO", Category.RESTAURANTES),
    ("DELIMEX SAS CEDRITOS", Category.RESTAURANTES),
    ("ABONO SUCURSAL VIRTUAL", Category.PAGO),
]


def seed(db) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for description_clean, category in EXAMPLES:
        exists = (
            db.query(CategoryExample)
            .filter(
                CategoryExample.description_clean == description_clean,
                CategoryExample.category == category,
            )
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(CategoryExample(description_clean=description_clean, category=category))
        inserted += 1
    db.commit()
    return inserted, skipped


if __name__ == "__main__":
    db = SessionLocal()
    try:
        inserted, skipped = seed(db)
        print(f"Seed complete: {inserted} inserted, {skipped} already existed.")
    finally:
        db.close()
