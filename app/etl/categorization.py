"""
Rules-first + LLM-fallback categorization.

Categories and keyword rules are loaded from the database (admin-managed).
User reclassifications feed back into rules via the keyword learner
(`app/etl/keyword_learner.py`), which promotes recurring tokens into
`category_keywords` with origin=LEARNED.

Usage:
    service = CategorizationService.from_db(db, llm_client=OpenRouterClient())
    result = service.categorize(normalized_tx)
"""
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.category import Category
from app.models.category_example import CategoryExample
from app.models.category_keyword import CategoryKeyword, KeywordOrigin
from app.models.enums import CategoryMethod
from app.services.llm_client import LLMError, OpenRouterClient

logger = logging.getLogger(__name__)

RULES_CONFIDENCE = Decimal("0.95")
OTROS_SLUG = "OTROS"

SYSTEM_PROMPT_TEMPLATE = """You are a personal finance transaction categorizer for Colombian bank statements.

Classify the transaction into EXACTLY ONE of these categories:
{categories}

Notes:
- INGRESO: money received into savings account (transfers in, interest, payments received)
- INVERSION: outflow to investment funds or financial products
- PAGO: credit card payments from savings account
- COBRO_BANCARIO: bank fees and government charges (e.g. "Cuota De Manejo", "4x1000 tax", maintenance fees, account fees)
- MOVIMIENTO_ENTRE_BANCOS: inter-bank transfers between own accounts (recargas, transfers to/from own Nequi/Bancolombia)

Rules:
- Return ONLY valid JSON, no markdown, no explanation outside the JSON.
- confidence must be between 0.0 and 1.0.
- If you are uncertain, use OTROS with low confidence.
- merchant should be a short clean name (e.g. "Spotify", "Uber", "Éxito").

Response format:
{{
  "category": "<CATEGORY>",
  "confidence": 0.0,
  "merchant": "<merchant name>",
  "reason": "<one sentence>"
}}"""


@dataclass
class CategorizationResult:
    category_id: uuid.UUID | None
    category_slug: str
    category_confidence: Decimal
    category_method: CategoryMethod
    merchant_guess: str | None


@dataclass
class _CategoryRule:
    category_id: uuid.UUID
    slug: str
    keywords: list[str]


class CategorizationService:
    def __init__(
        self,
        rules: list[_CategoryRule],
        slug_to_id: dict[str, uuid.UUID],
        examples: list[dict],
        llm_client: OpenRouterClient | None = None,
        user_overrides: dict[str, uuid.UUID] | None = None,
    ):
        """
        rules: per-category active keyword sets, ordered by category priority.
        slug_to_id: full active-category lookup (includes categories with no keywords).
        examples: list of dicts with keys description_clean, category (slug), merchant — for LLM context.
        user_overrides: description_clean -> category_id from user reclassifications;
            checked first, before rules and LLM.
        """
        self.rules = rules
        self.slug_to_id = slug_to_id
        self.examples = examples
        self.llm_client = llm_client
        self.user_overrides = user_overrides or {}
        self.allowed_slugs = set(slug_to_id.keys())

    @classmethod
    def from_db(cls, db: Session, llm_client: OpenRouterClient | None = None) -> "CategorizationService":
        """Build a categorizer from the current categories/keywords/examples in the DB."""
        # Active categories
        cats = db.query(Category).filter(Category.is_active.is_(True)).all()
        slug_to_id = {c.slug: c.id for c in cats}

        # Active keywords grouped by category — order categories with the more
        # specific slugs first (mirrors prior hardcoded RULES priority).
        priority_order = [
            "INGRESO", "MOVIMIENTO_ENTRE_BANCOS", "INVERSION", "PAGO",
            "COBRO_BANCARIO", "DOMICILIOS", "CARRO", "TRANSPORTE", "SALUD",
            "HOGAR", "RESTAURANTES", "OCIO", "PLATAFORMAS", "TRABAJO",
            "PRESTACIONES", "EDUCACION", "ROPA", "REGALOS",
        ]
        by_cat: dict[uuid.UUID, list[str]] = {}
        for kw in db.query(CategoryKeyword).filter(CategoryKeyword.is_active.is_(True)).all():
            by_cat.setdefault(kw.category_id, []).append(kw.keyword)

        rules: list[_CategoryRule] = []
        seen: set[uuid.UUID] = set()
        slug_priority = {s: i for i, s in enumerate(priority_order)}
        for cat in sorted(cats, key=lambda c: slug_priority.get(c.slug, 999)):
            kws = by_cat.get(cat.id)
            if not kws:
                continue
            rules.append(_CategoryRule(category_id=cat.id, slug=cat.slug, keywords=kws))
            seen.add(cat.id)

        # User overrides: exact description_clean -> category_id from
        # CategoryExample (which is upserted on every reclassification).
        user_overrides: dict[str, uuid.UUID] = {}
        for ex in db.query(CategoryExample).all():
            user_overrides[ex.description_clean] = ex.category_id

        # LLM examples context
        slug_by_id = {c.id: c.slug for c in cats}
        examples_dicts = [
            {
                "description_clean": ex.description_clean,
                "category": slug_by_id.get(ex.category_id, "OTROS"),
                "merchant": ex.merchant,
            }
            for ex in db.query(CategoryExample).all()
        ]

        return cls(
            rules=rules,
            slug_to_id=slug_to_id,
            examples=examples_dicts,
            llm_client=llm_client,
            user_overrides=user_overrides,
        )

    def categorize(self, normalized_tx: dict) -> CategorizationResult:
        # 0. User-override exact match (reclassifications are source of truth)
        result = self._apply_user_override(normalized_tx)
        if result:
            return result

        # 1. Rules-first
        result = self._apply_rules(normalized_tx)
        if result:
            return result

        # 2. LLM fallback
        if self.llm_client:
            result = self._apply_llm(normalized_tx)
            if result:
                return result

        # 3. Final fallback
        return CategorizationResult(
            category_id=self.slug_to_id.get(OTROS_SLUG),
            category_slug=OTROS_SLUG,
            category_confidence=Decimal("0.0"),
            category_method=CategoryMethod.LLM if self.llm_client else CategoryMethod.RULES,
            merchant_guess=None,
        )

    # ------------------------------------------------------------------
    # User overrides (from reclassifications)
    # ------------------------------------------------------------------

    def _apply_user_override(self, tx: dict) -> CategorizationResult | None:
        desc = tx.get("description_clean")
        if not desc:
            return None
        cat_id = self.user_overrides.get(desc)
        if not cat_id:
            return None
        slug = next((s for s, i in self.slug_to_id.items() if i == cat_id), OTROS_SLUG)
        return CategorizationResult(
            category_id=cat_id,
            category_slug=slug,
            category_confidence=Decimal("1.00"),
            category_method=CategoryMethod.USER,
            merchant_guess=desc[:30].strip().title(),
        )

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _apply_rules(self, tx: dict) -> CategorizationResult | None:
        text = (tx.get("description_clean") or tx.get("description_raw") or "").upper()
        for rule in self.rules:
            for kw in rule.keywords:
                if kw.upper() in text:
                    return CategorizationResult(
                        category_id=rule.category_id,
                        category_slug=rule.slug,
                        category_confidence=RULES_CONFIDENCE,
                        category_method=CategoryMethod.RULES,
                        merchant_guess=text[:30].strip().title(),
                    )
        return None

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _apply_llm(self, tx: dict) -> CategorizationResult | None:
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": self._build_user_message(tx)},
        ]
        try:
            raw = self.llm_client.chat(messages)
        except LLMError as exc:
            logger.warning("LLM categorization failed: %s", exc)
            return None

        return self._parse_llm_response(raw)

    def _system_prompt(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(categories=", ".join(sorted(self.allowed_slugs)))

    def _build_user_message(self, tx: dict) -> str:
        amount = tx.get("amount", "")
        currency = tx.get("currency", "COP")
        description_raw = tx.get("description_raw", "")
        description_clean = tx.get("description_clean", "")
        details = tx.get("details_json") or {}
        extra = details.get("extra_details") or []

        lines = [
            f"description_raw: {description_raw}",
            f"description_clean: {description_clean}",
            f"amount: {amount} {currency}",
        ]
        if extra:
            lines.append(f"extra_details: {', '.join(extra)}")

        if self.examples:
            lines.append("\nExamples:")
            for ex in self.examples:
                lines.append(f"  {ex['description_clean']} -> {ex['category']}")

        lines.append("\nClassify this transaction:")
        return "\n".join(lines)

    def _parse_llm_response(self, raw: dict) -> CategorizationResult | None:
        threshold = Decimal(str(settings.llm_confidence_threshold))

        slug = raw.get("category", "")
        confidence_raw = raw.get("confidence", 0.0)
        merchant = raw.get("merchant") or None

        if slug not in self.allowed_slugs:
            logger.warning("LLM returned invalid category: %s", slug)
            slug = OTROS_SLUG

        try:
            confidence = Decimal(str(confidence_raw)).quantize(Decimal("0.01"))
        except Exception:
            confidence = Decimal("0.0")

        if confidence < threshold:
            slug = OTROS_SLUG

        return CategorizationResult(
            category_id=self.slug_to_id.get(slug),
            category_slug=slug,
            category_confidence=confidence,
            category_method=CategoryMethod.LLM,
            merchant_guess=merchant,
        )
