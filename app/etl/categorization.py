"""
Rules-first + LLM-fallback categorization.

Usage:
    service = CategorizationService(examples=db_examples, llm_client=OpenRouterClient())
    result = service.categorize(normalized_tx)
"""
import logging
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import settings
from app.models.enums import Category, CategoryMethod
from app.services.llm_client import LLMError, OpenRouterClient

logger = logging.getLogger(__name__)

RULES: dict[str, list[str]] = {
    # More specific rules first to avoid false positives

    # Savings account: ingresos (positive amounts)
    Category.INGRESO: [
        "TRANSF DE", "TRANSFERENCIA DESDE NEQUI", "ABONO INTERESES AHORROS",
        "PAGO INTERBANC",
        # Nequi ingresos
        "RECIBI POR BRE-B DE", "Recarga desde Bancolombia", "Recarga en:",
        "Pago de Intereses", "De ",
    ],

    # Savings account: inversiones (negative amounts going to investment funds)
    Category.INVERSION: [
        "PAGO CORREVAL", "CORREVAL FIDUCIA",
        "PSE Credicorp Capital", "PAGO PSE Credicorp",
    ],

    # Savings account: pagos de tarjetas de crédito
    Category.PAGO: [
        "ABONO SUCURSAL VIRTUAL",
        "PAGO SUC VIRT TC",
    ],

    # Savings account: cobros bancarios
    Category.COBRO_BANCARIO: [
        "CUOTA DE MANEJO", "CUOTA MANEJO TRJ", "CUOTA MANEJO",
        "IMPTO GOBIERNO 4X1000", "4X1000",
        "COMISION BANCARIA", "COBRO BANCARIO",
    ],

    Category.DOMICILIOS: [
        "DLO*DIDI FOOD", "DIDI FOOD", "RAPPI",
    ],
    Category.CARRO: [
        "PARQUEADERO",
    ],
    Category.TRANSPORTE: [
        "DL DIDI RIDES", "DIDI RIDES", "DLO*DIDI", "UBER",
    ],
    Category.SALUD: [
        "FARMATODO", "DROGUERIA", "DROG", "IPS", "ACTION BLACK",
    ],
    Category.HOGAR: [
        "EXITO", "D1", "TIENDA D1", "HOMECENTER", "COMCEL",
        "PAGO FACTURA MOVIL", "TRANSF A ENEL", "TRANSF A VANTI",
    ],
    Category.RESTAURANTES: [
        "JUAN VALDEZ", "STARBUCKS", "IL FORNO", "PARMESSANO", "CAFE",
        "CREPESYWAFFLES", "HELADERIA", "DELIMEX", "SABORES NIKKEI",
        "MAESTRIA DEL FUEGO", "PASTIER", "BOLD*", "TJV", "GRUPO MURRI",
    ],
    Category.OCIO: [
        "SPOTIFY", "NETFLIX", "CINECITY", "MIRANDA DISCO", "BAR Y GRILL",
        "APPARTA", "APPLE.COM/BILL", "AEROREPUBLICA", "PRIORITY PASS",
        "FALABELLA", "AMAZON MKTPL", "PAYPAL", "MERCADOPAGO",
    ],
    Category.TRABAJO: [
        "OPENAI", "CHATGPT", "CLAUDE", "CURSOR", "OPENROUTER",
    ],
    Category.PRESTACIONES: [
        "PAGO CARDIF", "CARDIF",
    ],
}

RULES_CONFIDENCE = Decimal("0.95")
ALLOWED_CATEGORIES = {c.value for c in Category}

SYSTEM_PROMPT = """You are a personal finance transaction categorizer for Colombian bank statements.

Classify the transaction into EXACTLY ONE of these categories:
HOGAR, DOMICILIOS, CARRO, TRANSPORTE, OCIO, RESTAURANTES, ROPA, SALUD,
PRESTACIONES, REGALOS, EDUCACION, TRABAJO, COBRO_BANCARIO, PAGO, PLATAFORMAS,
INGRESO, INVERSION, OTROS

Notes:
- INGRESO: money received into savings account (transfers in, interest, payments received)
- INVERSION: outflow to investment funds or financial products
- PAGO: credit card payments from savings account
- COBRO_BANCARIO: bank fees and government charges (e.g. "Cuota De Manejo", "4x1000 tax", maintenance fees, account fees)

Rules:
- Return ONLY valid JSON, no markdown, no explanation outside the JSON.
- confidence must be between 0.0 and 1.0.
- If you are uncertain, use OTROS with low confidence.
- merchant should be a short clean name (e.g. "Spotify", "Uber", "Éxito").

Response format:
{
  "category": "<CATEGORY>",
  "confidence": 0.0,
  "merchant": "<merchant name>",
  "reason": "<one sentence>"
}"""


@dataclass
class CategorizationResult:
    category: Category
    category_confidence: Decimal
    category_method: CategoryMethod
    merchant_guess: str | None


class CategorizationService:
    def __init__(self, examples: list[dict], llm_client: OpenRouterClient | None = None):
        """
        examples: list of dicts with keys description_clean, category, merchant
        llm_client: optional; if None, LLM fallback is disabled
        """
        self.examples = examples
        self.llm_client = llm_client

    def categorize(self, normalized_tx: dict) -> CategorizationResult:
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
            category=Category.OTROS,
            category_confidence=Decimal("0.0"),
            category_method=CategoryMethod.LLM if self.llm_client else CategoryMethod.RULES,
            merchant_guess=None,
        )

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _apply_rules(self, tx: dict) -> CategorizationResult | None:
        text = (tx.get("description_clean") or tx.get("description_raw") or "").upper()
        for category, keywords in RULES.items():
            for kw in keywords:
                if kw.upper() in text:
                    return CategorizationResult(
                        category=category,
                        category_confidence=RULES_CONFIDENCE,
                        category_method=CategoryMethod.RULES,
                        merchant_guess=self._guess_merchant(text, kw),
                    )
        return None

    def _guess_merchant(self, text: str, matched_keyword: str) -> str:
        # Return the first 30 chars of the description as a rough merchant guess
        return text[:30].strip().title()

    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------

    def _apply_llm(self, tx: dict) -> CategorizationResult | None:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_message(tx)},
        ]
        try:
            raw = self.llm_client.chat(messages)
        except LLMError as exc:
            logger.warning("LLM categorization failed: %s", exc)
            return None

        return self._parse_llm_response(raw)

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

        category_str = raw.get("category", "")
        confidence_raw = raw.get("confidence", 0.0)
        merchant = raw.get("merchant") or None

        if category_str not in ALLOWED_CATEGORIES:
            logger.warning("LLM returned invalid category: %s", category_str)
            category_str = Category.OTROS.value

        try:
            confidence = Decimal(str(confidence_raw)).quantize(Decimal("0.01"))
        except Exception:
            confidence = Decimal("0.0")

        if confidence < threshold:
            category_str = Category.OTROS.value

        return CategorizationResult(
            category=Category(category_str),
            category_confidence=confidence,
            category_method=CategoryMethod.LLM,
            merchant_guess=merchant,
        )
