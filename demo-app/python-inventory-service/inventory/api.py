"""FastAPI routes for the inventory service."""

from fastapi import FastAPI, HTTPException

from inventory.models import Product, StockAdjustment
from inventory import service

app = FastAPI(title="Inventory Service", version="1.0.0")


@app.post("/products", response_model=Product, status_code=201)
def create_product(product: Product) -> Product:
    try:
        return service.add_product(product)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/products/{product_id}", response_model=Product)
def read_product(product_id: int) -> Product:
    try:
        return service.get_product(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/stock/adjust", response_model=Product)
def adjust_stock(adjustment: StockAdjustment) -> Product:
    try:
        return service.adjust_stock(adjustment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/stats/total-value")
def total_value() -> dict:
    return {"total_value": service.calculate_total_value()}


@app.get("/stats/average-price")
def avg_price() -> dict:
    return {"average_price": service.average_price()}
