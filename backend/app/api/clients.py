# backend/app/api/clients.py
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.supabase import supabase
from app.utils.auth import require_user

router = APIRouter()


@router.get("/", response_model=list[dict])
def list_clients(
    q: Optional[str] = Query(None, description="Filtro por nombre/email (ilike)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(require_user),
):
    """
    GET /clients/?q=ana&limit=50&offset=0
    Devuelve SOLO los clientes del owner actual (multi-tenant).
    """
    try:
        query = supabase.table("clients").select("*").eq("owner_id", user_id)

        if q:
            like = f"%{q}%"
            # filtra dentro del tenant (name OR email)
            query = query.or_(f"name.ilike.{like},email.ilike.{like}")

        start = offset
        end = offset + limit - 1  # Supabase range es inclusivo
        res = query.order("id", desc=False).range(start, end).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=dict, status_code=201)
def create_client(payload: dict, user_id: str = Depends(require_user)):
    """
    Crea un cliente para el owner actual; fuerza owner_id en servidor.
    """
    try:
        data = {**payload, "owner_id": user_id}
        res = (
            supabase.table("clients")
            .insert(data)
            .select("*")
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=400, detail="No se pudo crear el cliente")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{client_id}", response_model=dict)
def update_client(client_id: int, payload: dict, user_id: str = Depends(require_user)):
    """
    Actualiza el cliente solo si pertenece al owner actual.
    (Ignora cambios de owner_id en el payload)
    """
    try:
        data = {k: v for k, v in payload.items() if k != "owner_id"}
        res = (
            supabase.table("clients")
            .update(data)
            .eq("id", client_id)
            .eq("owner_id", user_id)
            .select("*")
            .single()
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return res.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, user_id: str = Depends(require_user)):
    """
    Borra el cliente solo si pertenece al owner actual.
    """
    try:
        supabase.table("clients").delete().eq("id", client_id).eq("owner_id", user_id).execute()
        return  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
