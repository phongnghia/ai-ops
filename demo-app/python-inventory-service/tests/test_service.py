"""Unit tests for inventory service.

Failing tests (demonstrate bugs for AI Ops analysis):
  BUG #1 — NameError in calculate_total_value() — always fails.
  BUG #2 — ZeroDivisionError in average_price() — always fails on empty store.
  BUG #3 — RuntimeError in apply_bulk_discount() — flaky, fails ~50% of runs.
"""

import pytest

from inventory.models import Product, StockAdjustment
from inventory import service


@pytest.fixture(autouse=True)
def clear_store():
    """Reset in-memory store before every test for isolation."""
    service.clear()
    yield
    service.clear()


def _make_product(pid: int = 1, qty: int = 10, price: float = 9.99) -> Product:
    return Product(id=pid, name=f"product-{pid}", quantity=qty,
                   price=price, category="test")


class TestAddProduct:
    def test_add_returns_product(self):
        p = _make_product()
        result = service.add_product(p)
        assert result.id == p.id

    def test_duplicate_raises(self):
        service.add_product(_make_product())
        with pytest.raises(ValueError, match="already exists"):
            service.add_product(_make_product())


class TestGetProduct:
    def test_get_existing(self):
        p = service.add_product(_make_product())
        assert service.get_product(p.id).name == p.name

    def test_get_missing_raises(self):
        with pytest.raises(KeyError, match="not found"):
            service.get_product(999)


class TestAdjustStock:
    def test_restock_increases_quantity(self):
        service.add_product(_make_product(qty=5))
        result = service.adjust_stock(StockAdjustment(product_id=1, delta=3))
        assert result.quantity == 8

    def test_sell_decreases_quantity(self):
        service.add_product(_make_product(qty=5))
        result = service.adjust_stock(StockAdjustment(product_id=1, delta=-3))
        assert result.quantity == 2

    def test_oversell_raises(self):
        service.add_product(_make_product(qty=2))
        with pytest.raises(ValueError, match="Insufficient stock"):
            service.adjust_stock(StockAdjustment(product_id=1, delta=-5))


class TestCalculateTotalValue:
    def test_total_value_with_products(self):
        """BUG #1: NameError — 'prodcut' is not defined.

        This test ALWAYS fails with:
          NameError: name 'prodcut' is not defined
        """
        service.add_product(_make_product(pid=1, qty=2, price=10.0))
        service.add_product(_make_product(pid=2, qty=3, price=5.0))

        total = service.calculate_total_value()

        assert total == pytest.approx(35.0)  # 2*10 + 3*5

    def test_total_value_empty_inventory(self):
        assert service.calculate_total_value() == 0.0


class TestAveragePrice:
    def test_average_with_products(self):
        service.add_product(_make_product(pid=1, price=10.0))
        service.add_product(_make_product(pid=2, price=20.0))
        assert service.average_price() == pytest.approx(15.0)

    def test_average_empty_raises(self):
        """BUG #2: ZeroDivisionError — len([]) == 0.

        This test ALWAYS fails because average_price() does not guard against
        an empty inventory:
          ZeroDivisionError: division by zero
        """
        result = service.average_price()
        assert result == 0.0


class TestApplyBulkDiscount:
    def test_discount_reduces_price(self):
        """BUG #3: RuntimeError — flaky, fails ~50% of runs.

        apply_bulk_discount() simulates a flaky external pricing service that
        raises RuntimeError on roughly half of all calls. Running the test
        suite multiple times will produce intermittent failures:

          RuntimeError: Pricing service temporarily unavailable

        This is the classic 'works on my machine' failure that motivates
        AI-assisted log analysis — the same code passes one run and fails
        the next.
        """
        service.add_product(_make_product(pid=1, price=100.0))

        updated = service.apply_bulk_discount(product_id=1, discount_pct=20)

        assert updated.price == pytest.approx(80.0)

    def test_invalid_discount_raises(self):
        service.add_product(_make_product(pid=1, price=100.0))
        with pytest.raises(ValueError, match="discount_pct"):
            service.apply_bulk_discount(product_id=1, discount_pct=150)

    def test_discount_missing_product_raises(self):
        with pytest.raises(KeyError, match="not found"):
            service.apply_bulk_discount(product_id=999, discount_pct=10)
