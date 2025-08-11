# backend/app/api/items.py
from __future__ import annotations

import os
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from pydantic import BaseModel, Field

from app.db.supabase import supabase
from app.utils.auth import require_user  # ← misma dependencia que en clients.py

router = APIRouter()

# ---------- Modelos ----------
class ItemIn(BaseModel):
    name: str
    price: float = Field(0, ge=0)
    stock: int = Field(0, ge=0)
    image_url: Optional[str] = None

class ItemOut(ItemIn):
    id: str

# ---------- Helpers ----------
def _like(value: str) -> str:
    return f"%{value.strip()}%"

MEDIA_ROOT = os.path.join(os.getcwd(), "media")
ITEMS_DIR = os.path.join(MEDIA_ROOT, "items")
os.makedirs(ITEMS_DIR, exist_ok=True)

# ---------- Endpoints ----------
@router.get("/", response_model=List[ItemOut])
def list_items(
    q: Optional[str] = Query(None, description="Búsqueda por nombre"),
    user_id: str = Depends(require_user),
):
    """
    Devuelve SOLO los items del owner actual (multi-tenant).
    Si hay error con Supabase, devolvemos [] para no romper el frontend.
    """
    try:
        query = supabase.table("items").select("*").eq("owner_id", user_id)
        if q:
            # si tu instancia soporta ilike en PostgREST:
            query = query.ilike("name", _like(q))

        res = query.order("name", desc=False).execute()
        rows = res.data or []

        out: List[ItemOut] = []
        for r in rows:
            out.append(
                ItemOut(
                    id=str(r.get("id")),
                    name=r.get("name") or "",
                    price=float(r.get("price") or 0),
                    stock=int(r.get("stock") or 0),
                    image_url=r.get("image_url"),
                )
            )
        return out

    except Exception as e:
        print("[/items] list_items ERROR:", repr(e))
        return []

@router.post("/", response_model=ItemOut, status_code=201)
def create_item(
    payload: ItemIn,
    user_id: str = Depends(require_user),
):
    """
    Crea item para el owner actual; fuerza owner_id del lado servidor.
    """
    try:
        data = {
            "name": payload.name,
            "price": float(payload.price or 0),
            "stock": int(payload.stock or 0),
            "image_url": payload.image_url or None,
            "owner_id": user_id,  # ← clave multi-tenant
        }
        res = supabase.table("items").insert(data).execute()

        if getattr(res, "error", None):
            detail = getattr(res.error, "message", str(res.error))
            raise HTTPException(status_code=400, detail=detail)

        if not res.data:
            raise HTTPException(status_code=400, detail="No se pudo crear el item")

        r = res.data[0]
        return ItemOut(
            id=str(r.get("id")),
            name=r.get("name") or "",
            price=float(r.get("price") or 0),
            stock=int(r.get("stock") or 0),
            image_url=r.get("image_url"),
        )
    except HTTPException:
        raise
    except Exception as e:
        print("[/items] create_item ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: str,
    user_id: str = Depends(require_user),
):
    """
    Elimina SOLO si el item pertenece al owner actual.
    """
    try:
        res = (
            supabase.table("items").delete().eq("id", item_id).eq("owner_id", user_id).execute()
        )

        if getattr(res, "error", None):
            detail = getattr(res.error, "message", str(res.error))
            raise HTTPException(status_code=400, detail=detail)
        return  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        print("[/items] delete_item ERROR:", repr(e))
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@router.post("/upload-image/", summary="Sube una imagen y devuelve su URL pública")
async def upload_item_image(
    file: UploadFile = File(...),
    user_id: str = Depends(require_user),
):
    """
    Guarda el archivo en ./media/items y devuelve {"image_url": "/media/items/<archivo>"}.
    """
    try:
        ts = int(time.time())
        safe_name = f"{ts}_{os.path.basename(file.filename)}".replace(" ", "_")
        disk_path = os.path.join(ITEMS_DIR, safe_name)

        content = await file.read()
        with open(disk_path, "wb") as f:
            f.write(content)

        public_url = f"/media/items/{safe_name}"
        return {"image_url": public_url}
    except Exception as e:
        print("[/items/upload-image] ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="No se pudo subir la imagen")
