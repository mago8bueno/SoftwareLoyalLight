# app/api/clients.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.db.supabase import supabase  # tu cliente existente

router = APIRouter()

@router.get("/", response_model=list[dict])
def list_clients(
    q: Optional[str] = Query(None, description="Filtro por nombre/email (ilike)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    GET /clients?q=ana&limit=50&offset=0
    Busca por nombre o email (ilike). Si no hay q, devuelve todos (paginado).
    """
    try:
        query = supabase.table("clients").select("*")

        if q:
            # or() de Supabase: name ilike o email ilike
            like = f"%{q}%"
            query = query.or_(f"name.ilike.{like},email.ilike.{like}")

        # Paginación (range usa ambos inclusive)
        start = offset
        end = offset + limit - 1
        res = query.order("id", desc=False).range(start, end).execute()

        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=dict, status_code=201)
def create_client(payload: dict):
    res = supabase.table("clients").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo crear el cliente")
    return res.data[0]


@router.put("/{client_id}", response_model=dict)
def update_client(client_id: int, payload: dict):
    res = supabase.table("clients").update(payload).eq("id", client_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return res.data[0]


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int):
    supabase.table("clients").delete().eq("id", client_id).execute()
    return {"ok": True}
