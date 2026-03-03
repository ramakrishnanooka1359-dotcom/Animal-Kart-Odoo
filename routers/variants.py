from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from odoo_client import execute
from config import ANIMAL_KART_COMPANY_ID

router = APIRouter()


class SingleVariantResponse(BaseModel):
    id: int
    name: str
    product_template_id: int
    price: float
    warehouse_stock: Dict[str, float]


@router.get(
    "/variant/{variant_id}",
    response_model=SingleVariantResponse,
    tags=["Variants"],
    summary="Get single variant with warehouse-wise stock"
)
def get_single_variant(variant_id: int):

    # Get active variant for company 2 only
    variant = execute(
        "product.product",
        "search_read",
        [[
            ("id", "=", variant_id),
            ("company_id", "=", ANIMAL_KART_COMPANY_ID),
            ("active", "=", True)
        ]],
        {
            "fields": [
                "id",
                "display_name",
                "product_tmpl_id",
                "lst_price"
            ]
        }
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found in Animal Kart company"
        )

    variant = variant[0]

    # Get active warehouses
    warehouses = execute(
        "stock.warehouse",
        "search_read",
        [[
            ("company_id", "=", ANIMAL_KART_COMPANY_ID),
            ("active", "=", True)
        ]],
        {"fields": ["id", "name", "view_location_id"]}
    )

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

    return {
        "id": variant["id"],
        "name": variant["display_name"],
        "product_template_id": variant["product_tmpl_id"][0],
        "price": variant["lst_price"],
        "warehouse_stock": warehouse_stock
    }