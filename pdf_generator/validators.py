"""Разбор денежных значений и проверка полей документа."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from pdf_generator.config import MONEY_QUANTUM

_SPACES = re.compile(r"[\s\u00a0]+")


class MoneyFormatError(ValueError):
    """Цену нельзя разобрать как денежную сумму."""


class NegativeMoneyError(ValueError):
    """Цена меньше нуля."""


class QuantityFormatError(ValueError):
    """Количество нельзя разобрать как число."""


class NonPositiveQuantityError(ValueError):
    """Количество равно нулю или отрицательное."""


class PaymentDaysError(ValueError):
    """Срок оплаты не является целым неотрицательным числом."""


def quantize_money(value: Decimal) -> Decimal:
    """Округлить денежную сумму до копеек по правилу ROUND_HALF_UP."""
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def parse_money(value: Any) -> Decimal:
    """Разобрать цену и привести её к двум знакам после запятой.

    Отрицательные значения отклоняются. Ноль допустим.
    """
    amount = _to_decimal(value, MoneyFormatError)
    if amount < 0:
        raise NegativeMoneyError(str(value))
    return quantize_money(amount)


def parse_quantity(value: Any) -> Decimal:
    """Разобрать количество. Оно должно быть строго больше нуля."""
    quantity = _to_decimal(value, QuantityFormatError)
    if quantity <= 0:
        raise NonPositiveQuantityError(str(value))
    return _normalize_quantity(quantity)


def parse_payment_days(value: Any) -> int:
    """Разобрать срок действия счёта в днях."""
    if isinstance(value, bool) or value is None:
        raise PaymentDaysError(str(value))
    if isinstance(value, str):
        text = value.strip()
        if not re.fullmatch(r"\d+", text):
            raise PaymentDaysError(value)
        return int(text)
    if isinstance(value, Decimal):
        if not value.is_finite() or value != value.to_integral_value() or value < 0:
            raise PaymentDaysError(str(value))
        return int(value)
    if isinstance(value, int):
        if value < 0:
            raise PaymentDaysError(str(value))
        return value
    if isinstance(value, float):
        if not value.is_integer() or value < 0:
            raise PaymentDaysError(str(value))
        return int(value)
    raise PaymentDaysError(str(value))


def is_blank(value: Any) -> bool:
    """Пустое значение: None или строка из пробелов."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def as_text(value: Any) -> str:
    """Преобразовать реквизит в текст, не теряя длинные целые числа."""
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, Decimal):
        if not value.is_finite():
            return ""
        if value == value.to_integral_value():
            return str(value.to_integral_value())
        return format(value, "f")
    if isinstance(value, float):
        decimal_value = Decimal(str(value))
        return as_text(decimal_value)
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _to_decimal(value: Any, error_type: type[ValueError]) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise error_type(str(value))
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        # str(float) даёт кратчайшую десятичную запись, без двоичного хвоста.
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        text = _SPACES.sub("", value.strip())
        if not text or _has_mixed_separators(text):
            raise error_type(value)
        text = text.replace(",", ".")
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:
            raise error_type(value) from exc
    else:
        raise error_type(str(value))

    if not decimal_value.is_finite():
        raise error_type(str(value))
    return decimal_value


def _has_mixed_separators(text: str) -> bool:
    return "," in text and "." in text


def _normalize_quantity(value: Decimal) -> Decimal:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return Decimal(rendered)
