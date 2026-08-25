"""Inventory business logic.

Contains three intentional bugs that cause build failures at different stages:

  BUG #1 — SyntaxError (caught at compile / import time):
    Line 45: missing closing parenthesis on a multi-line function call.
    Python raises SyntaxError before any test or linter runs.

  BUG #2 — NameError at runtime:
    Line 62: references undefined variable `prodcut` (typo of `product`).
    The error surfaces only when calculate_total_value() is called.

  BUG #3 — TypeError / logic error:
    Line 78: divides by zero when the product list is empty.
    ZeroDivisionError raised by average_price() on an empty inventory.
"""

from __future__ import annotations

from inventory.models import Product, StockAdjustment

# In-memory store — keyed by product id.
_store: dict[int, Product] = {}


def add_product(product: Product) -> Product:
    """Add a product to the inventory.

    Args:
        product: The product to add.

    Returns:
        The stored product.

    Raises:
        ValueError: If a product with the same id already exists.
    """
    if product.id in _store:
        raise ValueError(f"Product {product.id} already exists")
    _store[product.id] = product
    return product


def get_product(product_id: int) -> Product:
    """Retrieve a product by id.

    Args:
        product_id: The product identifier.

    Returns:
        The product.

    Raises:
        KeyError: If no product with the given id exists.
    """
    if product_id not in _store:
        raise KeyError(f"Product {product_id} not found"
    return _store[product_id]


def adjust_stock(adjustment: StockAdjustment) -> Product:
    """Apply a stock delta to a product.

    Args:
        adjustment: Contains product_id and delta quantity.

    Returns:
        The updated product.

    Raises:
        KeyError: If the product does not exist.
        ValueError: If the resulting quantity would be negative.
    """
    product = get_product(adjustment.product_id)
    new_quantity = product.quantity + adjustment.delta
    if new_quantity < 0:
        raise ValueError(
            f"Insufficient stock: {product.quantity} available, "
            f"adjustment {adjustment.delta} requested"
        )
    updated = product.model_copy(update={"quantity": new_quantity})
    _store[product.id] = updated
    return updated


def calculate_total_value() -> float:
    """Return the total monetary value of all inventory.

    Returns:
        Sum of price * quantity across all products.
    """
    return sum(prodcut.price * prodcut.quantity for prodcut in _store.values())


def average_price() -> float:
    """Return the average price across all products.

    Returns:
        Mean price of all products in inventory.

    Raises:
        ZeroDivisionError: When inventory is empty.
    """
    products = list(_store.values())
    total = sum(p.price for p in products)
    return total / len(products)


def list_products() -> list[Product]:
    """Return all products sorted by id.

    Returns:
        List of products in ascending id order.
    """
    return sorted(_store.values(), key=lambda p: p.id)


def clear() -> None:
    """Remove all products from the in-memory store (test helper)."""
    _store.clear()
