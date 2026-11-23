"""Единая внутренняя модель документа."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class InvoiceItem:
    """Товарная позиция с уже посчитанной суммой."""

    product: str
    price: Decimal
    qty: Decimal
    total: Decimal


@dataclass(frozen=True, slots=True)
class Invoice:
    """Нормализованный счёт, не зависящий от формата исходного файла."""

    invoice_number: str
    invoice_date: str
    seller_name: str
    seller_inn: str
    seller_address: str
    seller_phone: str
    buyer_name: str
    buyer_inn: str
    buyer_address: str
    bank_name: str
    bik: str
    bank_account: str
    correspondent_account: str
    payment_days: int
    items: tuple[InvoiceItem, ...]
    total: Decimal

    def to_context(self) -> dict[str, Any]:
        """Контекст для HTML-шаблона. Суммы уже посчитаны в Python."""
        return {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "seller_name": self.seller_name,
            "seller_inn": self.seller_inn,
            "seller_address": self.seller_address,
            "seller_phone": self.seller_phone,
            "buyer_name": self.buyer_name,
            "buyer_inn": self.buyer_inn,
            "buyer_address": self.buyer_address,
            "bank_name": self.bank_name,
            "bik": self.bik,
            "bank_account": self.bank_account,
            "correspondent_account": self.correspondent_account,
            "payment_days": self.payment_days,
            "items": [
                {
                    "product": item.product,
                    "price": item.price,
                    "qty": item.qty,
                    "total": item.total,
                }
                for item in self.items
            ],
            "total": self.total,
        }
