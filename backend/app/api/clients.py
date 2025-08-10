# app/api/clients.py  
from fastapi import APIRouter, Query, HTTPException, Depends  
from typing import Optional  
from app.db.supabase import supabase  
from app.utils.auth import require_user  
  
router = APIRouter()  
  
@router.get("/", response_model=list[dict])  
def list_clients(  
    q: Optional[str] = Query(None, description="Filtro por nombre/email (ilike)"),  
    limit: int = Query(50, ge=1, le=200),  
    offset: int = Query(0, ge=0),  
    user_id: str = Depends(require_user),   # 👈 Reemplaza ambas dependencias anteriores  
):  
    """  
    GET /clients/?q=ana&limit=50&offset=0  
    Devuelve SOLO los clientes del owner (multi-tenant).  
    """  
    try:  
        query = supabase.table("clients").select("*").eq("owner_id", user_id)  # 👈 Usa user_id directamente  
  
        if q:  
            like = f"%{q}%"  
            # filtra dentro del tenant  
            query = query.or_(f"name.ilike.{like},email.ilike.{like}")  
  
        start = offset  
        end = offset + limit - 1  
        res = query.order("id", desc=False).range(start, end).execute()  
        return res.data or []  
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))  
  
@router.post("/", response_model=dict, status_code=201)  
def create_client(payload: dict, user_id: str = Depends(require_user)):  # 👈  
    """  
    Crea cliente para el owner actual; fuerza owner_id del lado servidor.  
    """  
    try:  
        data = {**payload, "owner_id": user_id}  # 👈 Simplificado  
        res = supabase.table("clients").insert(data).select("*").single().execute()  
        if not res.data:  
            raise HTTPException(status_code=400, detail="No se pudo crear el cliente")  
        return res.data  
    except HTTPException:  
        raise  
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))  
  
@router.put("/{client_id}", response_model=dict)  
def update_client(client_id: int, payload: dict, user_id: str = Depends(require_user)):  # 👈  
    """  
    Actualiza solo si la fila pertenece al owner.  
    """  
    try:  
        # Nunca permitir cambiar owner_id vía payload  
        data = {k: v for k, v in payload.items() if k != "owner_id"}  
  
        res = (  
            supabase.table("clients")  
            .update(data)  
            .eq("id", client_id)  
            .eq("owner_id", user_id)  # 👈 Usa user_id directamente  
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
def delete_client(client_id: int, user_id: str = Depends(require_user)):  # 👈  
    """  
    Borra solo si la fila pertenece al owner.  
    """  
    try:  
        supabase.table("clients").delete().eq("id", client_id).eq("owner_id", user_id).execute()  # 👈  
        return {"ok": True}  
    except HTTPException:  
        raise  
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))
