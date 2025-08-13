# backend/app/api/ai.py
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List, Optional, Union
from app.db.supabase import supabase
from app.services.openai_service import OpenAIService
import logging

router = APIRouter()
openai_service = OpenAIService()
logger = logging.getLogger(__name__)


@router.get("/recommendations", summary="Recomendaciones IA con OpenAI", tags=["ai"])
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
    Genera recomendaciones usando OpenAI GPT basadas en el perfil del cliente.
    - Si pasas client_id => recomendaciones personalizadas para ese cliente.
    - Si NO pasas client_id => devuelve top clientes en riesgo con recomendaciones.
    """
    try:
        if client_id is not None:
            q = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("client_id", client_id)
                .limit(1)
            )
            if tenant_id:
                q = q.eq("tenant_id", tenant_id)
            res = q.execute()
            if getattr(res, "error", None):
                detail = getattr(res.error, "message", str(res.error))
                raise HTTPException(status_code=400, detail=detail)
            if not res.data:
                raise HTTPException(
                    status_code=404, detail="Cliente no encontrado en v_churn_risk"
                )
            client_data = res.data[0]

            purchases_q = (
                supabase.table("purchases")
                .select("*, items(*)")
                .eq("client_id", client_id)
                .order("created_at", desc=True)
                .limit(10)
            )
            if tenant_id:
                purchases_q = purchases_q.eq("tenant_id", tenant_id)
            purchases_res = purchases_q.execute()
            if getattr(purchases_res, "error", None):
                detail = getattr(purchases_res.error, "message", str(purchases_res.error))
                raise HTTPException(status_code=400, detail=detail)
            purchase_history = purchases_res.data or []

            try:
                ai_recommendations = openai_service.generate_client_recommendations(
                    client_data, purchase_history
                )
            except Exception as e:
                logger.error("OpenAI recommendation error: %s", e)
                raise HTTPException(status_code=502, detail=str(e))

            return {
                "client": {
                    "id": client_data["client_id"],
                    "name": client_data.get("name"),
                    "email": client_data.get("email"),
                    "churn_score": int(client_data.get("churn_score") or 0),
                },
                "recommendations": ai_recommendations,
                "ai_powered": True,
            }

        q = (
            supabase.table("v_churn_risk")
            .select("*")
            .order("churn_score", desc=True)
            .limit(limit)
        )
        if tenant_id:
            q = q.eq("tenant_id", tenant_id)
        res = q.execute()
        if getattr(res, "error", None):
            detail = getattr(res.error, "message", str(res.error))
            raise HTTPException(status_code=400, detail=detail)

        items: List[Dict[str, Any]] = []
        for client_data in res.data or []:
            purchases_q = (
                supabase.table("purchases")
                .select("*, items(*)")
                .eq("client_id", client_data["client_id"])
                .order("created_at", desc=True)
                .limit(5)
            )
            if tenant_id:
                purchases_q = purchases_q.eq("tenant_id", tenant_id)
            purchases_res = purchases_q.execute()
            if getattr(purchases_res, "error", None):
                detail = getattr(purchases_res.error, "message", str(purchases_res.error))
                raise HTTPException(status_code=400, detail=detail)
            purchase_history = purchases_res.data or []
            try:
                ai_recommendations = openai_service.generate_client_recommendations(
                    client_data, purchase_history
                )
            except Exception as e:
                logger.error("OpenAI recommendation error: %s", e)
                raise HTTPException(status_code=502, detail=str(e))

            items.append(
                {
                    "client": {
                        "id": client_data["client_id"],
                        "name": client_data.get("name"),
                        "email": client_data.get("email"),
                        "churn_score": int(client_data.get("churn_score") or 0),
                    },
                    "recommendations": ai_recommendations,
                    "ai_powered": True,
                }
            )

        return {"items": items}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/ai/recommendations] error: %s", repr(e))
        raise HTTPException(status_code=500, detail="No se pudieron calcular recomendaciones")


@router.get(
    "/clients/{client_id}/suggestions",
    summary="Sugerencias IA personalizadas con OpenAI",
    tags=["ai"],
)
def client_suggestions(
    client_id: Union[str, int],
    tenant_id: Optional[str] = Query(
        None, description="Tenant opcional para filtrar compras del cliente"
    ),
) -> Dict[str, Any]:
    """
    Genera sugerencias personalizadas usando OpenAI basadas en el historial completo del cliente.
    """
    try:
        client_q = supabase.table("clients").select("*").eq("id", client_id).limit(1)
        if tenant_id:
            client_q = client_q.eq("tenant_id", tenant_id)
        client_res = client_q.execute()
        if getattr(client_res, "error", None):
            detail = getattr(client_res.error, "message", str(client_res.error))
            raise HTTPException(status_code=400, detail=detail)
        if not client_res.data:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        client_data = client_res.data[0]

        purchases_q = (
            supabase.table("purchases")
            .select("*, items(*)")
            .eq("client_id", client_id)
            .order("created_at", desc=True)
            .limit(20)
        )
        if tenant_id:
            purchases_q = purchases_q.eq("tenant_id", tenant_id)
        purchases_res = purchases_q.execute()
        if getattr(purchases_res, "error", None):
            detail = getattr(purchases_res.error, "message", str(purchases_res.error))
            raise HTTPException(status_code=400, detail=detail)
        purchase_history = purchases_res.data or []

        churn_res = (
            supabase.table("v_churn_risk")
            .select("*")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        if getattr(churn_res, "error", None):
            detail = getattr(churn_res.error, "message", str(churn_res.error))
            raise HTTPException(status_code=400, detail=detail)
        churn_data = churn_res.data[0] if churn_res.data else {}
        churn_score = int(churn_data.get("churn_score") or 0)
        last_purchase_days = int(churn_data.get("last_purchase_days") or 0)
        top_item_id = churn_data.get("top_item_id")

        try:
            suggestions = openai_service.generate_client_suggestions(
                client_data, purchase_history, last_purchase_days
            )
        except Exception as e:
            logger.error("OpenAI suggestion error: %s", e)
            raise HTTPException(status_code=502, detail=str(e))

        return {
            "client_id": client_id,
            "churn_score": churn_score,
            "last_purchase_days": last_purchase_days,
            "top_item_id": top_item_id,
            "suggestions": suggestions,
            "ai_powered": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/ai/clients/{client_id}/suggestions] error: %s", repr(e))
        raise HTTPException(status_code=500, detail="No se pudieron calcular sugerencias")
