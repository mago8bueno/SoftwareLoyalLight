# app/api/clients.py  
from typing import Optional  
from fastapi import APIRouter, Query, HTTPException, Header, Depends  
  
from app.db.supabase import supabase  
from app.core.security import get_current_user  
  
router = APIRouter()  
  
  
# --- helper para extraer el owner desde el header ---  
def get_owner_id(x_user_id: Optional[str] = Header(None, convert_underscores=False)) -> str:  
    """  
    Lee X-User-Id (uuid del usuario/owner). Si falta, 401.  
    Nota: convert_underscores=False para respetar el nombre exacto 'X-User-Id'.  
    """  
    if not x_user_id:  
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")  
    return x_user_id  
  
  
@router.get("/", response_model=list[dict])  
def list_clients(  
    q: Optional[str] = Query(None, description="Filtro por nombre/email (ilike)"),  
    limit: int = Query(50, ge=1, le=200),  
    offset: int = Query(0, ge=0),  
    owner_id: str = Depends(get_owner_id),  
    current_user: dict = Depends(get_current_user),  # ← Autenticación JWT agregada  
):  
    """  
    GET /clients/?q=ana&limit=50&offset=0  
    Devuelve SOLO los clientes del owner (multi-tenant).  
    """  
    try:  
        query = supabase.table("clients").select("*").eq("owner_id", owner_id)  
  
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
def create_client(  
    payload: dict,   
    owner_id: str = Depends(get_owner_id),  
    current_user: dict = Depends(get_current_user),  # ← Autenticación JWT agregada  
):  
    """  
    Crea cliente para el owner actual; fuerza owner_id del lado servidor.  
    """  
    try:  
        data = dict(payload)  
        data["owner_id"] = owner_id  # clave: no confiar en el cliente  
        res = supabase.table("clients").insert(data).select("*").single().execute()  
        if not res.data:  
            raise HTTPException(status_code=400, detail="No se pudo crear el cliente")  
        return res.data  
    except HTTPException:  
        raise  
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))  
  
  
@router.put("/{client_id}", response_model=dict)  
def update_client(  
    client_id: int,   
    payload: dict,   
    owner_id: str = Depends(get_owner_id),  
    current_user: dict = Depends(get_current_user),  # ← Autenticación JWT agregada  
):  
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
            .eq("owner_id", owner_id)  
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
def delete_client(  
    client_id: int,   
    owner_id: str = Depends(get_owner_id),  
    current_user: dict = Depends(get_current_user),  # ← Autenticación JWT agregada  
):  
    """  
    Borra solo si la fila pertenece al owner.  
    """  
    try:  
        res = (  
            supabase.table("clients")  
            .delete()  
            .eq("id", client_id)  
            .eq("owner_id", owner_id)  
            .execute()  
        )  
        # Si no borró nada, era de otro tenant o no existía  
        if getattr(res, "count", None) == 0:  
            raise HTTPException(status_code=404, detail="Cliente no encontrado")  
        return {"ok": True}  
    except HTTPException:  
        raise  
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))
