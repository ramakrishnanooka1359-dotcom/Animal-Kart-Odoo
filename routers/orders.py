from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from odoo_client import execute
from config import ANIMAL_KART_COMPANY_ID

router = APIRouter()


# -----------------------------
# REQUEST MODELS
# -----------------------------

class OrderLineRequest(BaseModel):
    product_id: int   # Variant ID
    quantity: float


class OrderRequest(BaseModel):
    partner_id: int
    warehouse_id: int
    order_lines: List[OrderLineRequest]


# -----------------------------
# CREATE ORDER API
# -----------------------------

@router.post(
    "/orders",
    tags=["Orders"],
    summary="Create Order, Confirm, Deliver and Generate Invoice"
)
def create_order(order: OrderRequest):

    # 1️⃣ Create Sale Order
    order_id = execute(
        "sale.order",
        "create",
        [{
            "partner_id": order.partner_id,
            "company_id": ANIMAL_KART_COMPANY_ID,
            "warehouse_id": order.warehouse_id,
            "order_line": [
                (0, 0, {
                    "product_id": line.product_id,
                    "product_uom_qty": line.quantity,
                    "product_uom": 29,  # Pair (1 Pair = 2 Animals) in 'Animals' category
                    "price_unit": 350000.0  # 175000 * 2
                }) for line in order.order_lines
            ]
        }]
    )

    if not order_id:
        raise HTTPException(status_code=400, detail="Failed to create order")

    # 2️⃣ Confirm Order
    execute(
        "sale.order",
        "action_confirm",
        [[order_id]]
    )

    # 3️⃣ Get Delivery Pickings
    order_data = execute(
        "sale.order",
        "read",
        [[order_id]],
        {"fields": ["picking_ids"]}
    )
    
    picking_ids = order_data[0].get("picking_ids", []) if order_data else []

    # 4️⃣ Assign & Validate Delivery
    for picking_id in picking_ids:

        # Reserve stock
        execute("stock.picking", "action_assign", [[picking_id]])

        # Get move lines with move_id
        move_lines = execute(
            "stock.move.line",
            "search_read",
            [[("picking_id", "=", picking_id)]],
            {"fields": ["id", "move_id"]}
        )

        for move in move_lines:
            move_id = move["move_id"][0]  # get stock.move ID

            # Read ordered quantity from stock.move
            move_data = execute(
                "stock.move",
                "read",
                [[move_id]],
                {"fields": ["product_uom_qty"]}
            )

            ordered_qty = move_data[0]["product_uom_qty"]

            # Set qty_done = ordered quantity
            execute(
                "stock.move.line",
                "write",
                [[move["id"]], {
                    "qty_done": ordered_qty
                }]
            )   

        # Validate delivery
        execute("stock.picking", "button_validate", [[picking_id]])

    # 5️⃣ Create Invoice via Wizard (CORRECT WAY)
    wizard_id = execute(
        "sale.advance.payment.inv",
        "create",
        [{
            "advance_payment_method": "delivered",
        }],
        {
            "context": {
                "active_model": "sale.order",
                "active_ids": [order_id]
            }
        }
    )

    execute(
        "sale.advance.payment.inv",
        "create_invoices",
        [[wizard_id]],
        {
            "context": {
                "active_model": "sale.order",
                "active_ids": [order_id]
            }
        }
    )

    # 6️⃣ Get Created Invoice IDs
    invoice_data = execute(
        "sale.order",
        "read",
        [[order_id]],
        {"fields": ["invoice_ids"]}
    )

    invoice_ids = invoice_data[0].get("invoice_ids", []) if invoice_data else []

    invoice_status = []

    # 7️⃣ Post Invoice and Fetch Status
    for invoice_id in invoice_ids:

        # Post invoice
        execute("account.move", "action_post", [[invoice_id]])

        # Read invoice details
        invoice_info = execute(
            "account.move",
            "read",
            [[invoice_id]],
            {
                "fields": ["payment_state", "state"]
            }
        )

        if invoice_info:
            invoice_status.append(invoice_info[0])

    # 8️⃣ Final Response
    return {
        "message": "Order created, delivered and invoiced successfully",
        "order_id": order_id,
        "picking_ids": picking_ids,
        "invoice_ids": invoice_ids,
        "invoice_details": invoice_status
    }
  