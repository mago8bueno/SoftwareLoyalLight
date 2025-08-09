# purchases.py - Endpoints CRUD y lógica de compra

from fastapi import APIRouter, HTTPException, status
from typing import List
from uuid import UUID

from app.models.purchase import PurchaseCreate, PurchaseOut
from app.db.supabase import supabase

router = APIRouter()

@router.post("/", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(payload: PurchaseCreate):
    """Registra una nueva compra, actualiza stock y calcula total."""
    item_res = supabase.table("items").select("price,stock").eq("id", payload.item_id).single().execute()
    if not item_res.data or payload.quantity > item_res.data["stock"]:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    total_price = payload.quantity * item_res.data["price"]
    # Actualizar stock
    supabase.table("items").update({"stock": item_res.data["stock"] - payload.quantity}).eq("id", payload.item_id).execute()

    purchase_data = payload.dict()
    purchase_data.update({"total_price": total_price})
    res = supabase.table("purchases").insert(purchase_data).execute()
    if res.error:
        raise HTTPException(status_code=400, detail=res.error.message)

    return PurchaseOut(**res.data[0])

@router.get("/", response_model=List[PurchaseOut])
async def list_purchases():
    """Lista todas las compras."""
    res = supabase.table("purchases").select("*").execute()
    return [PurchaseOut(**row) for row in res.data]