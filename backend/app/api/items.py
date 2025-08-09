# backend/app/api/items.py
from __future__ import annotations

import os
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

from app.db.supabase import supabase  # tu instancia existente

router = APIRouter()

# ---------- Modelos ----------
class ItemIn(BaseModel):
    name: str
    price: float = Field(0, ge=0)
    stock: int = Field(0, ge=0)
    image_url: Optional[str] = None

class ItemOut(ItemIn):
    id: int

# ---------- Helpers ----------
def _like(value: str) -> str:
    # Para búsquedas case-insensitive si tu vista/tabla lo soporta
    return f"%{value.strip()}%"

MEDIA_ROOT = os.path.join(os.getcwd(), "media")
ITEMS_DIR = os.path.join(MEDIA_ROOT, "items")
os.makedirs(ITEMS_DIR, exist_ok=True)

# ---------- Endpoints ----------
@router.get("/", response_model=List[ItemOut])
def list_items(q: Optional[str] = Query(None, description="Búsqueda por nombre")):
    """
    Lista de items. Si hay cualquier problema con Supabase,
    devolvemos [] y lo dejamos logeado para no romper el frontend.
    """
    try:
        query = supabase.table("items").select("*")
        if q:
            # Si tu PostgREST / Supabase no soporta ilike aquí, puedes quitar esta línea.
            # Alternativa: traer todos y filtrar en Python.
            query = query.ilike("name", _like(q))
        # Orden alfabético por comodidad
        res = query.order("name", desc=False).execute()
        rows = res.data or []
        # Normalización mínima por seguridad
        out: List[ItemOut] = []
        for r in rows:
            out.append(ItemOut(
                id=int(r["id"]),
                name=r.get("name") or "",
                price=float(r.get("price") or 0),
                stock=int(r.get("stock") or 0),
                image_url=r.get("image_url"),
            ))
        return out
    except Exception as e:
        print("[/items] list_items ERROR:", repr(e))
        # Modo “tolerante” para que el frontend no muera si hay RLS/columnas/etc.
        return []

@router.post("/", response_model=ItemOut, status_code=201)
def create_item(payload: ItemIn):
    try:
        data = {
            "name": payload.name,
            "price": float(payload.price or 0),
            "stock": int(payload.stock or 0),
            "image_url": payload.image_url or None,
        }
        res = supabase.table("items").insert(data).select("*").single().execute()
        if not res.data:
            raise HTTPException(status_code=400, detail="No se pudo crear el item")
        r = res.data
        return ItemOut(
            id=int(r["id"]),
            name=r.get("name") or "",
            price=float(r.get("price") or 0),
            stock=int(r.get("stock") or 0),
            image_url=r.get("image_url"),
        )
    except HTTPException:
        raise
    except Exception as e:
        print("[/items] create_item ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="No se pudo crear el item")

@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int):
    try:
        supabase.table("items").delete().eq("id", item_id).execute()
        return
    except Exception as e:
        print("[/items] delete_item ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="No se pudo borrar el item")

@router.post("/upload-image/", summary="Sube una imagen y devuelve su URL pública")
async def upload_item_image(file: UploadFile = File(...)):
    """
    Guarda el archivo en ./media/items y devuelve {"image_url": "/media/items/<archivo>"}.
    Asegúrate de que en main.py montaste:
        app.mount("/media", StaticFiles(directory="media"), name="media")
    """
    try:
        # Nombre seguro (timestamp + nombre original)
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
