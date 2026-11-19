"""Pure normalization of synthetic Enable Banking AIS responses.

No HTTP, credentials, consent, filesystem or MCP registration. This is a separately
reviewable experiment, not a live provider adapter. Provider extras are discarded.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

class InvalidProviderData(ValueError):
    pass


def _fail():
    raise InvalidProviderData("Invalid provider response") from None


def _text(value, maximum=512):
    if not isinstance(value, str) or len(value) > maximum:
        _fail()
    return value


def _iso(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        _fail()
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail()
    return value


def _money(value, allow_negative=False):
    if not isinstance(value, dict):
        _fail()
    currency = value.get("currency")
    # XXX means no currency, not an unknown exchange rate. Preserve it as unknown.
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        _fail()
    raw = value.get("amount")
    if not isinstance(raw, str) or not re.fullmatch(r"-?[0-9]{1,15}(?:\.[0-9]{1,8})?", raw):
        _fail()
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        _fail()
    if not amount.is_finite() or (not allow_negative and amount < 0):
        _fail()
    return currency, amount


def normalize_transaction(record):
    """Return bounded data without IBANs, counterparties or provider identifiers.

    Transaction date wins, then booking date, then value date. A fallback date is
    labeled, never silently presented as the purchase date. Missing dates remain
    unknown. This is not expense classification or bank-history completeness.
    """
    if not isinstance(record, dict):
        _fail()
    currency, amount = _money(record.get("transaction_amount"))
    indicator = record.get("credit_debit_indicator")
    status = record.get("status")
    if not isinstance(indicator, str) or not isinstance(status, str) or indicator not in {"CRDT", "DBIT"} or status not in {"BOOK", "PDNG"}:
        _fail()
    if indicator == "DBIT":
        amount = amount.copy_negate()
    dates = {}
    for key in ("transaction_date", "booking_date", "value_date"):
        if key in record and record[key] is not None:
            dates[key] = _iso(record[key])
    source = next((key for key in ("transaction_date", "booking_date", "value_date") if key in dates), None)
    remittance = record.get("remittance_information", [])
    if not isinstance(remittance, list) or len(remittance) > 8:
        _fail()
    description = "\n".join(_text(part, 512) for part in remittance)
    if len(description) > 1024:
        _fail()
    return {
        "amount": format(amount.copy_abs() if amount.is_zero() else amount, "f"), "currency": currency,
        "currency_known": currency != "XXX",
        "status": {"BOOK": "booked", "PDNG": "pending"}[status],
        "date": dates.get(source), "date_source": source,
        "date_inferred": source not in {None, "transaction_date"},
        "description": description,
    }


def normalize_balances(payload):
    """Keep balance types separate. Never sum booked and available balances."""
    if not isinstance(payload, dict) or not isinstance(payload.get("balances"), list):
        _fail()
    if len(payload["balances"]) > 20:
        _fail()
    result = []
    for record in payload["balances"]:
        if not isinstance(record, dict):
            _fail()
        currency, amount = _money(record.get("balance_amount"), allow_negative=True)
        kind = _text(record.get("balance_type"), 12)
        if not re.fullmatch(r"[A-Z0-9]{1,12}", kind):
            _fail()
        reference = record.get("reference_date")
        result.append({"amount": format(amount.copy_abs() if amount.is_zero() else amount, "f"), "currency": currency,
                       "currency_known": currency != "XXX", "type": kind,
                       "reference_date": _iso(reference) if reference is not None else None})
    return result


def normalize_page(payload):
    """Normalize one page, not automatic fetching. Empty+cursor means incomplete.

    Cursor is an opaque bounded token, never a URL, request target or public tool
    parameter. The caller of a future adapter must add page/time/byte budgets,
    repeat-token detection and redirect refusal before following any cursor.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("transactions"), list):
        _fail()
    records = payload["transactions"]
    if len(records) > 100:
        _fail()
    cursor = payload.get("continuation_key")
    if cursor is not None:
        _text(cursor, 2048)
        if not cursor:
            _fail()
    return {"transactions": [normalize_transaction(record) for record in records],
            "continuation_key": cursor, "complete": cursor is None}
