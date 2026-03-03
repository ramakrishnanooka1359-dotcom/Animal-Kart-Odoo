from fastapi import APIRouter
from typing import List, Dict
from pydantic import BaseModel
from odoo_client import execute
from config import ANIMAL_KART_COMPANY_ID

router = APIRouter()


class VariantStock(BaseModel):
    id: int
    name: str
    warehouse_stock: Dict[str, float]


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    variants: List[VariantStock]


@router.get(
    "/products",
    response_model=List[ProductResponse],
    tags=["Products"],
    summary="Get all products with variants and warehouse stock"
)
def get_products():

    warehouses = execute(
        "stock.warehouse",
        "search_read",
        [[
            ("company_id", "=", ANIMAL_KART_COMPANY_ID),
            ("active", "=", True)
        ]],
        {"fields": ["id", "name", "view_location_id"]}
    )

    products = execute(
        "product.template",
        "search_read",
        [[
            ("company_id", "=", ANIMAL_KART_COMPANY_ID),
            ("active", "=", True)
        ]],
        {"fields": ["id", "name", "list_price", "product_variant_ids"]}
    )

    final_data = []

    for product in products:

        variants = execute(
            "product.product",
            "search_read",
            [[
                ("id", "in", product["product_variant_ids"]),
                ("company_id", "=", ANIMAL_KART_COMPANY_ID),
                ("active", "=", True)
            ]],
            {"fields": ["id", "display_name"]}
        )

        variants_data = []

        for variant in variants:

            warehouse_stock = {}

            for wh in warehouses:
                location_id = wh["view_location_id"][0]

                quants = execute(
                    "stock.quant",
                    "search_read",
                    [[
                        ("product_id", "=", variant["id"]),
                        ("location_id", "child_of", location_id)
                    ]],
                    {"fields": ["quantity"]}
                )

                total_qty = sum(q["quantity"] for q in quants)
                warehouse_stock[wh["name"]] = total_qty

            variants_data.append({
                "id": variant["id"],
                "name": variant["display_name"],
                "warehouse_stock": warehouse_stock
            })

        final_data.append({
            "id": product["id"],
            "name": product["name"],
            "price": product["list_price"],
            "variants": variants_data
        })

    return final_data