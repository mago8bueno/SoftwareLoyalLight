# backend/app/api/purchases.py
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.purchase import PurchaseCreate, PurchaseOut
from app.db.supabase import supabase
from app.utils.auth import require_user  # ← obtiene user_id desde el JWT

router = APIRouter()

@router.post("/", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate,
    user_id: str = Depends(require_user),   # ← owner actual
):
    """
    Registra una compra SOLO si item y cliente pertenecen al mismo owner.
    Actualiza stock y calcula total.
    """
    # 1) Verificar item pertenece al owner y stock
    item_res = (
        supabase.table("items")
        .select("price,stock,owner_id")
        .eq("id", payload.item_id)
        .single()
        .execute()
    )
    item = getattr(item_res, "data", None)
    if not item or item.get("owner_id") != user_id:
        raise HTTPException(status_code=404, detail="Item no encontrado para este usuario")
    if payload.quantity > (item.get("stock") or 0):
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    # 2) Verificar cliente pertenece al owner
    client_res = (
        supabase.table("clients")
        .select("owner_id")
        .eq("id", payload.client_id)
        .single()
        .execute()
    )
    client = getattr(client_res, "data", None)
    if not client or client.get("owner_id") != user_id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado para este usuario")

    # 3) Calcular total y actualizar stock
    total_price = float(payload.quantity) * float(item["price"])
    supabase.table("items").update(
        {"stock": int(item["stock"]) - int(payload.quantity)}
    ).eq("id", payload.item_id).execute()

    # 4) Insertar compra con owner_id
    purchase_data = payload.dict()
    purchase_data.update({"total_price": total_price, "owner_id": user_id})

    res = (
        supabase.table("purchases")
        .insert(purchase_data)
        .select("*")
        .single()
        .execute()
    )
    if getattr(res, "error", None):
        # res.error puede ser None en versiones nuevas; por si acaso:
        msg = getattr(res.error, "message", "No se pudo crear la compra")
        raise HTTPException(status_code=400, detail=msg)

    return PurchaseOut(**res.data)


@router.get("/", response_model=List[PurchaseOut])
async def list_purchases(
    user_id: str = Depends(require_user),
):
    """Lista SOLO las compras del owner."""
    res = supabase.table("purchases").select("*").eq("owner_id", user_id).execute()
    rows = getattr(res, "data", []) or []
    return [PurchaseOut(**row) for row in rows]
