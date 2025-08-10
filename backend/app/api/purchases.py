# backend/app/api/purchases.py
from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import List, Optional

from app.models.purchase import PurchaseCreate, PurchaseOut
from app.db.supabase import supabase

router = APIRouter()

def get_owner_id(x_user_id: Optional[str] = Header(None, convert_underscores=False)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id

@router.post("/", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(payload: PurchaseCreate, owner_id: str = Depends(get_owner_id)):
    """
    Registra compra SOLO si el item y el cliente pertenecen al mismo owner.
    """
    # 1. Verificar que el item es del owner
    item_res = supabase.table("items").select("price,stock,owner_id").eq("id", payload.item_id).single().execute()
    if not item_res.data or item_res.data["owner_id"] != owner_id:
        raise HTTPException(status_code=404, detail="Item no encontrado para este usuario")
    if payload.quantity > item_res.data["stock"]:
        raise HTTPException(status_code=400, detail="Stock insuficiente")

    # 2. Verificar que el cliente es del owner
    client_res = supabase.table("clients").select("owner_id").eq("id", payload.client_id).single().execute()
    if not client_res.data or client_res.data["owner_id"] != owner_id:
        raise HTTPException(status_code=404, detail="Cliente no encontrado para este usuario")

    # 3. Calcular total y actualizar stock
    total_price = payload.quantity * item_res.data["price"]
    supabase.table("items").update({"stock": item_res.data["stock"] - payload.quantity}).eq("id", payload.item_id).execute()

    # 4. Insertar compra con owner_id
    purchase_data = payload.dict()
    purchase_data.update({
        "total_price": total_price,
        "owner_id": owner_id
    })
    res = supabase.table("purchases").insert(purchase_data).select("*").single().execute()
    if res.error:
        raise HTTPException(status_code=400, detail=res.error.message)

    return PurchaseOut(**res.data)

@router.get("/", response_model=List[PurchaseOut])
async def list_purchases(owner_id: str = Depends(get_owner_id)):
    """
    Lista SOLO las compras del owner.
    """
    res = supabase.table("purchases").select("*").eq("owner_id", owner_id).execute()
    return [PurchaseOut(**row) for row in (res.data or [])]
