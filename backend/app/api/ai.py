# backend/app/api/ai.py
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional, Union
from app.db.supabase import supabase  # instancia ya existente

router = APIRouter()


def _basic_reco(churn_score: int) -> List[str]:
    """
    Reglas simples de recomendación basadas en churn_score.
    """
    if churn_score >= 80:
        return [
            "Enviar cupón del 20% con caducidad 7 días",
            "Llamada personalizada desde soporte",
            "Sugerir productos complementarios del último pedido",
        ]
    if churn_score >= 60:
        return [
            "Enviar cupón del 10%",
            "Email de recuperación con novedades",
        ]
    if churn_score >= 40:
        return [
            "Recordatorio de items vistos/guardados",
            "Ofrecer suscripción con descuento",
        ]
    return [
        "Programa de fidelización (puntos)",
        "Recomendaciones por historial",
    ]


@router.get(
    "/recommendations",
    summary="Recomendaciones IA (reglas simples)",
    tags=["ai"],
)
def recommendations(
    client_id: Optional[Union[str, int]] = Query(
        None, description="ID de cliente (opcional; admite UUID o entero)"
    ),
    limit: int = Query(5, ge=1, le=50),
    tenant_id: Optional[str] = Query(
        None,
        description="Tenant opcional para filtrar datos (si tu schema es multi-tenant)",
    ),
) -> Dict[str, Any]:
    """
    - Si pasas client_id => recomendaciones para ese cliente (usa v_churn_risk).
    - Si NO pasas client_id => devuelve top clientes en riesgo (limit).
    - tenant_id (opcional) añade filtro eq('tenant_id', tenant_id) si tu vista lo expone.
    """
    try:
        if client_id is not None:
            q = supabase.table("v_churn_risk").select("*").eq("client_id", client_id).limit(1)
            if tenant_id:
                q = q.eq("tenant_id", tenant_id)

            res = q.execute()
            if not res.data:
                raise HTTPException(status_code=404, detail="Cliente no encontrado en v_churn_risk")

            row = res.data[0]
            score = int(row.get("churn_score") or 0)
            return {
                "client": {
                    "id": row["client_id"],
                    "name": row.get("name"),
                    "email": row.get("email"),
                    "churn_score": score,
                },
                "recommendations": _basic_reco(score),
            }

        # Top clientes en riesgo
        q = supabase.table("v_churn_risk").select("*").order("churn_score", desc=True).limit(limit)
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)

        res = q.execute()
        items: List[Dict[str, Any]] = []
        for r in res.data or []:
            score = int(r.get("churn_score") or 0)
            items.append(
                {
                    "client": {
                        "id": r["client_id"],
                        "name": r.get("name"),
                        "email": r.get("email"),
                        "churn_score": score,
                    },
                    "recommendations": _basic_reco(score),
                }
            )
        return {"items": items}

    except HTTPException:
        raise
    except Exception as e:
        print("[/ai/recommendations] error:", repr(e))
        raise HTTPException(status_code=500, detail="No se pudieron calcular recomendaciones")


@router.get(
    "/clients/{client_id}/suggestions",
    summary="Sugerencias IA por cliente (heurística simple)",
    tags=["ai"],
)
def client_suggestions(
    client_id: Union[str, int],  # <- ACEPTA UUID o entero
    tenant_id: Optional[str] = Query(
        None, description="Tenant opcional para filtrar compras del cliente"
    ),
) -> Dict[str, Any]:
    """
    Heurística muy simple:
    - Mira compras recientes del cliente.
    - Adivina su “producto favorito” (más repetido).
    - Calcula churn por días desde la última compra.
    - Devuelve acciones sugeridas (descuento/bundle).
    """
    try:
        q = (
            supabase.table("purchases")
            .select("id, item_id, quantity, created_at")
            .eq("client_id", client_id)   # <- sin cast a int
            .order("created_at", desc=True)
            .limit(20)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)

        purchases = (q.execute()).data or []

        from collections import Counter
        top_item_id = None
        if purchases:
            top_item_id = Counter([p["item_id"] for p in purchases]).most_common(1)[0][0]

        import datetime as dt
        last_iso = max([p["created_at"] for p in purchases], default=None)
        if last_iso:
            last_dt = dt.datetime.fromisoformat(str(last_iso).replace("Z", "+00:00"))
            days = (dt.datetime.now(dt.timezone.utc) - last_dt).days
        else:
            days = 999

        churn_score = 90 if days > 120 else 70 if days > 90 else 50 if days > 60 else 10

        return {
            "client_id": client_id,
            "churn_score": churn_score,
            "last_purchase_days": days,
            "top_item_id": top_item_id,
            "suggestions": [
                {"type": "discount", "text": "Cupón 10% en su producto favorito"},
                {"type": "bundle", "text": "Pack con su último producto + accesorio"},
            ],
        }
    except Exception as e:
        print("[/ai/clients/{id}/suggestions] error:", repr(e))
        raise HTTPException(status_code=500, detail="No se pudieron obtener sugerencias")
