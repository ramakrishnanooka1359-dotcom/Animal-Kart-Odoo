from fastapi import FastAPI
from routers.products import router as products_router
from routers.variants import router as variants_router
from routers.orders import router as orders_router

app = FastAPI(
    title="Animal Kart API",
    description="Backend APIs for Animal Kart (Company ID = 2)",
    version="1.0.0"
)


@app.get("/", tags=["System"])
def home():
    return {"message": "Animal Kart API Running"}


# Include Routers
app.include_router(products_router)
app.include_router(variants_router)
app.include_router(orders_router)
