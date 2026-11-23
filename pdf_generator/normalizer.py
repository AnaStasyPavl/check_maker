"""Приведение CSV и JSON к единой модели счёта."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any, Mapping

from pdf_generator.config import ACCOUNT_FIELDS, STRING_INVOICE_FIELDS
from pdf_generator.exceptions import ValidationError
from pdf_generator.models import Invoice, InvoiceItem
from pdf_generator.validators import (
    MoneyFormatError,
    NegativeMoneyError,
    NonPositiveQuantityError,
    PaymentDaysError,
    QuantityFormatError,
    as_text,
    is_blank,
    parse_money,
    parse_payment_days,
    parse_quantity,
    quantize_money,
)

logger = logging.getLogger(__name__)

_SCIENTIFIC = re.compile(r"^[+-]?\d+(?:[.,]\d+)?[eE][+-]?\d+$")


def normalize_invoice(raw: Mapping[str, Any]) -> Invoice:
    """Проверить исходный документ, посчитать суммы и вернуть ``Invoice``.

    Суммы из исходного файла игнорируются и всегда пересчитываются.
    """
    errors: list[str] = []
    prefix = _document_prefix(raw)
    values: dict[str, Any] = {}

    for field in STRING_INVOICE_FIELDS:
        if field not in raw or is_blank(raw.get(field)):
            errors.append(_message(prefix, f"отсутствует обязательное поле «{field}»"))
            continue
        text = as_text(raw.get(field))
        if not text:
            errors.append(_message(prefix, f"отсутствует обязательное поле «{field}»"))
            continue
        values[field] = text
        if field in ACCOUNT_FIELDS:
            _warn_scientific(prefix, field, text)

    if "payment_days" not in raw or is_blank(raw.get("payment_days")):
        errors.append(_message(prefix, "отсутствует обязательное поле «payment_days»"))
    else:
        try:
            values["payment_days"] = parse_payment_days(raw.get("payment_days"))
        except PaymentDaysError:
            errors.append(
                _message(
                    prefix,
                    "некорректное значение payment_days "
                    f"«{raw.get('payment_days')}»: ожидается целое число не меньше нуля",
                )
            )

    items, item_errors = _normalize_items(raw, prefix)
    errors.extend(item_errors)
    if errors:
        raise ValidationError(errors)

    total = quantize_money(sum((item.total for item in items), Decimal("0.00")))
    return Invoice(
        invoice_number=values["invoice_number"],
        invoice_date=values["invoice_date"],
        seller_name=values["seller_name"],
        seller_inn=values["seller_inn"],
        seller_address=values["seller_address"],
        seller_phone=values["seller_phone"],
        buyer_name=values["buyer_name"],
        buyer_inn=values["buyer_inn"],
        buyer_address=values["buyer_address"],
        bank_name=values["bank_name"],
        bik=values["bik"],
        bank_account=values["bank_account"],
        correspondent_account=values["correspondent_account"],
        payment_days=values["payment_days"],
        items=tuple(items),
        total=total,
    )


def _normalize_items(
    raw: Mapping[str, Any],
    prefix: str,
) -> tuple[list[InvoiceItem], list[str]]:
    errors: list[str] = []
    payload = raw.get("items", None)
    if not isinstance(payload, list):
        return [], [_message(prefix, "поле «items» должно быть массивом товаров")]
    if len(payload) == 0:
        return [], [_message(prefix, "нет ни одного товара")]

    items: list[InvoiceItem] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, Mapping):
            errors.append(_message(prefix, f"позиция {index} должна быть объектом"))
            continue
        item_prefix = _item_prefix(prefix, item, index)
        product = item.get("product")
        if is_blank(product):
            errors.append(_message(item_prefix, "отсутствует обязательное поле «product»"))
            product_text = ""
        else:
            product_text = as_text(product)

        price: Decimal | None = None
        if "price" not in item or is_blank(item.get("price")):
            errors.append(_message(item_prefix, "отсутствует обязательное поле «price»"))
        else:
            try:
                price = parse_money(item.get("price"))
            except NegativeMoneyError:
                errors.append(
                    _message(
                        item_prefix,
                        f"цена не может быть отрицательной ({item.get('price')})",
                    )
                )
            except MoneyFormatError:
                errors.append(
                    _message(
                        item_prefix,
                        f"некорректный формат цены «{item.get('price')}»",
                    )
                )

        quantity: Decimal | None = None
        if "qty" not in item or is_blank(item.get("qty")):
            errors.append(_message(item_prefix, "отсутствует обязательное поле «qty»"))
        else:
            try:
                quantity = parse_quantity(item.get("qty"))
            except NonPositiveQuantityError:
                errors.append(
                    _message(
                        item_prefix,
                        f"количество должно быть больше нуля ({item.get('qty')})",
                    )
                )
            except QuantityFormatError:
                errors.append(
                    _message(
                        item_prefix,
                        f"некорректный формат количества «{item.get('qty')}»",
                    )
                )

        if product_text and price is not None and quantity is not None:
            line_total = quantize_money(price * quantity)
            items.append(
                InvoiceItem(
                    product=product_text,
                    price=price,
                    qty=quantity,
                    total=line_total,
                )
            )
    return items, errors


def _document_prefix(raw: Mapping[str, Any]) -> str:
    parts: list[str] = []
    source = raw.get("source")
    if source:
        parts.append(str(source))
    number = raw.get("invoice_number")
    if not is_blank(number):
        parts.append(f"счёт {as_text(number)}")
    elif raw.get("document_index"):
        parts.append(f"документ {raw['document_index']}")
    return ": ".join(parts)


def _item_prefix(prefix: str, item: Mapping[str, Any], index: int) -> str:
    kind = str(item.get("line_kind") or "позиция")
    line = item.get("line", index)
    location = f"{kind} {line}"
    if prefix:
        return f"{prefix}: {location}"
    return location


def _message(prefix: str, text: str) -> str:
    if prefix:
        return f"{prefix}: {text}"
    return text


def _warn_scientific(prefix: str, field: str, value: str) -> None:
    compact = value.replace(" ", "")
    if _SCIENTIFIC.fullmatch(compact):
        where = f"{prefix}: " if prefix else ""
        logger.warning(
            "%sполе «%s» содержит число в научной нотации (%s). "
            "Excel часто так портит длинные номера счетов и БИК. "
            "Перед выгрузкой CSV задайте этим столбцам текстовый формат.",
            where,
            field,
            value,
        )

