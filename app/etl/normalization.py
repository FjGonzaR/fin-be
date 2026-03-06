from decimal import Decimal

from app.utils.text import normalize_text


def normalize_rappicard_transaction(raw_tx: dict) -> dict:
    """
    Normalize a RappiCard/Davivienda raw transaction into canonical format.

    Canonical amount convention:
    - Expenses (valor_transaccion > 0) => NEGATIVE amount
    - Credits/payments (valor_transaccion < 0) => POSITIVE amount
    """
    valor = raw_tx["valor_transaccion"]

    if valor > 0:
        canonical_amount = -valor
    else:
        canonical_amount = abs(valor)

    description_raw = raw_tx["description_raw"]
    description_clean = normalize_text(description_raw)

    details: dict = {"card_type": raw_tx["card_type"]}
    for key in ("capital_facturado", "cuotas_raw", "capital_pendiente", "tasa_mv", "tasa_ea"):
        val = raw_tx.get(key)
        if val is not None:
            details[key] = str(val)

    return {
        "posted_at": raw_tx["posted_at"],
        "description_raw": description_raw,
        "description_clean": description_clean,
        "amount": canonical_amount,
        "details_json": details,
    }


def normalize_transaction(raw_tx: dict) -> dict:
    """
    Normalize a raw transaction into canonical format.

    Canonical amount convention:
    - Expenses (valor_movimiento > 0) => NEGATIVE amount
    - Credits (valor_movimiento < 0) => POSITIVE amount
    """
    valor_movimiento = raw_tx["valor_movimiento"]

    # Apply canonical sign convention
    if valor_movimiento > 0:
        # Expense
        canonical_amount = -valor_movimiento
    else:
        # Credit (already negative, so abs makes it positive)
        canonical_amount = abs(valor_movimiento)

    # Build description
    description_raw = raw_tx["movimientos"]
    if raw_tx.get("extra_details"):
        description_raw += " " + " ".join(raw_tx["extra_details"])

    description_clean = normalize_text(description_raw)

    # Build details_json
    details = {
        "auth_number": raw_tx["auth_number"],
    }

    if raw_tx.get("cuotas_raw"):
        details["cuotas"] = raw_tx["cuotas_raw"]

    if raw_tx.get("valor_cuota") is not None:
        details["valor_cuota"] = str(raw_tx["valor_cuota"])

    if raw_tx.get("interes_mensual") is not None:
        details["interes_mensual"] = str(raw_tx["interes_mensual"])

    if raw_tx.get("interes_anual") is not None:
        details["interes_anual"] = str(raw_tx["interes_anual"])

    if raw_tx.get("saldo_pendiente") is not None:
        details["saldo_pendiente"] = str(raw_tx["saldo_pendiente"])

    if raw_tx.get("extra_details"):
        details["extra_details"] = raw_tx["extra_details"]

    return {
        "posted_at": raw_tx["posted_at"],
        "description_raw": description_raw,
        "description_clean": description_clean,
        "amount": canonical_amount,
        "details_json": details,
    }
