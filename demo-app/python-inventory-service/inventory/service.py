"""Inventory business logic.

Contains three intentional bugs for AI Ops demo purposes:

  BUG #1 — NameError (always fails):
    calculate_total_value() references undefined variable `prodcut` (typo of
    `product`). Surfaces as NameError at test time.

  BUG #2 — ZeroDivisionError (always fails on empty inventory):
    average_price() calls len(products) without guarding against an empty
    list. The test that checks this case deliberately passes an empty store.

  BUG #3 — Random RuntimeError (flaky — fails ~50% of the time):
    apply_bulk_discount() uses random.random() to simulate flaky external
    dependency behaviour. Every other run raises RuntimeError:
    "Pricing service temporarily unavailable". Produces intermittent CI
    failures that are harder to diagnose than deterministic ones — exactly
    the kind of noise that motivates AI-assisted log analysis.
"""

from __future__ import annotations

import random

from inventory.models import Product, StockAdjustment

# In-memory store — keyed by product id.
_store: dict[int, Product] = {}

# Fixed seed used by tests that want deterministic behaviour.
# The demo pipeline never sets this, so apply_bulk_discount stays flaky.
_RANDOM_SEED: int | None = None


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
        raise KeyError(f"Product {product_id} not found")
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
    # BUG #1: typo 'prodcut' instead of 'product' — NameError at runtime.
    return sum(prodcut.price * prodcut.quantity for prodcut in _store.values())


def average_price() -> float:
    """Return the average price across all products.

    Returns:
        Mean price of all products in the inventory.

    Raises:
        ZeroDivisionError: When inventory is empty (BUG #2).
    """
    products = list(_store.values())
    total = sum(p.price for p in products)
    # BUG #2: no guard — raises ZeroDivisionError when products is empty.
    return total / len(products)


def apply_bulk_discount(product_id: int, discount_pct: float) -> Product:
    """Apply a bulk discount to a product price via an external pricing service.

    Simulates a flaky network call to an external pricing service. The call
    succeeds roughly half the time; the other half it raises RuntimeError to
    mimic a transient service unavailability. This produces intermittent CI
    failures (BUG #3) that appear random and are difficult to reproduce
    locally.

    Args:
        product_id: The product to discount.
        discount_pct: Discount as a percentage between 0 and 100.

    Returns:
        The updated product with the reduced price.

    Raises:
        KeyError: If the product does not exist.
        ValueError: If discount_pct is outside [0, 100].
        RuntimeError: Randomly (~50% of calls) when the pricing service
            is simulated as unavailable (BUG #3).
    """
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"discount_pct must be between 0 and 100, got {discount_pct}")

    product = get_product(product_id)

    rng = random.Random(_RANDOM_SEED)
    # BUG #3: simulated flaky external dependency — fails ~50% of runs.
    if rng.random() < 0.5:
        raise RuntimeError(
            "Pricing service temporarily unavailable "
            f"(product_id={product_id}, discount_pct={discount_pct})"
        )

    discounted_price = round(product.price * (1 - discount_pct / 100), 2)
    updated = product.model_copy(update={"price": discounted_price})
    _store[product.id] = updated
    return updated


def list_products() -> list[Product]:
    """Return all products sorted by id.

    Returns:
        List of products in ascending id order.
    """
    return sorted(_store.values(), key=lambda p: p.id)


def clear() -> None:
    """Remove all products from the in-memory store (test helper)."""
    _store.clear()
