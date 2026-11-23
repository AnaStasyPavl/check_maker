from pathlib import Path

from pdf_generator.loader import load_invoices


def test_load_json_invoice(tmp_path: Path) -> None:
    source = tmp_path / "invoice.json"
    source.write_text(
        """
        {
          "invoice_number": "TEST-1",
          "invoice_date": "23.11.2026",
          "seller_name": "ООО Продавец",
          "seller_inn": "7701234567",
          "seller_address": "Москва",
          "seller_phone": "+7 495 123-45-67",
          "buyer_name": "ООО Покупатель",
          "buyer_inn": "7809876543",
          "buyer_address": "Санкт-Петербург",
          "bank_name": "Сбербанк",
          "bik": "044525225",
          "bank_account": "40702810000000000001",
          "correspondent_account": "30101810400000000225",
          "payment_days": 5,
          "items": [{"product": "Тестовый товар", "price": 100.00, "qty": 2}]
        }
        """,
        encoding="utf-8",
    )

    invoices = load_invoices(source)

    assert len(invoices) == 1
    assert invoices[0].invoice_number == "TEST-1"
    assert str(invoices[0].total) == "200.00"
