"""
Promote tokens that recur in user reclassifications to LEARNED keywords.

Triggered after each reclassification (PATCH /transactions/{id}/categorize).
For every meaningful token in `description_clean`, look at all CategoryExamples
that contain that token. If one category dominates (>= MIN_OCCURRENCES rows
and >= MIN_PURITY share), upsert a CategoryKeyword(origin=LEARNED) so future
classifications match it via the rules engine.
"""
import logging
import re
import uuid
from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.category_example import CategoryExample
from app.models.category_keyword import CategoryKeyword, KeywordOrigin

logger = logging.getLogger(__name__)

MIN_TOKEN_LENGTH = 4
MIN_OCCURRENCES = 3
MIN_PURITY = 0.7

# Generic finance/transaction tokens that should never become keywords on their own.
STOPWORDS: set[str] = {
    "PAGO", "COMPRA", "ABONO", "CARGO", "DEBITO", "CREDITO", "TRANSFER",
    "TRANSFERENCIA", "TRANSF", "DESDE", "HACIA", "PARA", "POR", "CON", "DEL",
    "LOS", "LAS", "UNA", "UNO", "ESTE", "ESTA", "ESTO", "AHORROS", "CUENTA",
    "BANCO", "BANCA", "MOVIL", "WEB", "APP", "ONLINE", "VIRTUAL", "OFICINA",
    "CALLE", "CARRERA", "AVENIDA", "SUC", "SUCURSAL", "CIUDAD", "COL", "BOG",
    "BOGOTA", "MEDELLIN", "CALI", "COP", "USD", "DLS", "FACT", "FACTURA",
    "REF", "NRO", "NUMERO",
}

_TOKEN_RE = re.compile(r"[A-ZÁÉÍÓÚÑ0-9]{%d,}" % MIN_TOKEN_LENGTH)


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    upper = text.upper()
    tokens = set(_TOKEN_RE.findall(upper))
    return {t for t in tokens if t not in STOPWORDS}


def learn_from_reclassification(
    db: Session,
    description_clean: str,
    category_id: uuid.UUID,
) -> list[uuid.UUID]:
    """
    Run after a user reclassification. Returns list of CategoryKeyword IDs
    inserted/updated. Caller is responsible for committing.
    """
    tokens = _tokenize(description_clean)
    if not tokens:
        return []

    affected: list[uuid.UUID] = []

    for token in tokens:
        like_pattern = f"%{token}%"
        rows = (
            db.query(CategoryExample.category_id, func.count().label("cnt"))
            .filter(func.upper(CategoryExample.description_clean).like(like_pattern))
            .group_by(CategoryExample.category_id)
            .all()
        )
        if not rows:
            continue

        counter = Counter({r.category_id: r.cnt for r in rows})
        total = sum(counter.values())
        top_cat, top_cnt = counter.most_common(1)[0]

        if top_cat != category_id:
            # The category we just reclassified to is not the dominant one
            # for this token; skip — wait until it is.
            continue
        if top_cnt < MIN_OCCURRENCES:
            continue
        if (top_cnt / total) < MIN_PURITY:
            continue

        existing = (
            db.query(CategoryKeyword)
            .filter(
                CategoryKeyword.category_id == category_id,
                func.upper(CategoryKeyword.keyword) == token,
            )
            .first()
        )
        if existing:
            existing.weight = top_cnt
            existing.is_active = True
            if existing.origin == KeywordOrigin.LEARNED:
                affected.append(existing.id)
        else:
            kw = CategoryKeyword(
                category_id=category_id,
                keyword=token,
                origin=KeywordOrigin.LEARNED,
                weight=top_cnt,
                is_active=True,
            )
            db.add(kw)
            db.flush()
            affected.append(kw.id)
            logger.info("Learned keyword '%s' -> category %s (count=%d)", token, category_id, top_cnt)

    return affected
