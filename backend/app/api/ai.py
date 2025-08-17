# backend/app/api/ai.py
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional, Union
from app.db.supabase import supabase
from app.services.openai_service import OpenAIService
from app.utils.auth import require_user
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
    user_id: str = Depends(require_user),  # ← AÑADIDO: Autenticación
) -> Dict[str, Any]:
    """
    Genera recomendaciones usando OpenAI GPT basadas en el perfil del cliente.
    - Si pasas client_id => recomendaciones personalizadas para ese cliente.
    - Si NO pasas client_id => devuelve top clientes en riesgo con recomendaciones.
    """
    try:
        if client_id is not None:
            # Recomendaciones para UN cliente específico
            
            # 1. Verificar que el cliente pertenece al usuario
            client_check = (
                supabase.table("clients")
                .select("owner_id")
                .eq("id", client_id)
                .eq("owner_id", user_id)  # ← SEGURIDAD: Solo clientes del usuario
                .single()
                .execute()
            )
            
            if not client_check.data:
                raise HTTPException(
                    status_code=404, 
                    detail="Cliente no encontrado o no pertenece a tu cuenta"
                )
            
            # 2. Obtener datos del cliente desde la vista de churn
            churn_q = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("client_id", client_id)
                .eq("owner_id", user_id)  # ← SEGURIDAD
                .single()
            )
            
            churn_res = churn_q.execute()
            if getattr(churn_res, "error", None):
                detail = getattr(churn_res.error, "message", str(churn_res.error))
                raise HTTPException(status_code=400, detail=detail)
                
            if not churn_res.data:
                raise HTTPException(
                    status_code=404, 
                    detail="Datos de churn no encontrados para este cliente"
                )
                
            client_data = churn_res.data

            # 3. Obtener historial de compras del cliente
            purchases_q = (
                supabase.table("purchases")
                .select("*, items(*)")
                .eq("client_id", client_id)
                .eq("owner_id", user_id)  # ← SEGURIDAD
                .order("purchased_at", desc=True)
                .limit(10)
            )
            
            purchases_res = purchases_q.execute()
            if getattr(purchases_res, "error", None):
                detail = getattr(purchases_res.error, "message", str(purchases_res.error))
                logger.warning(f"Error obteniendo compras: {detail}")
                # No fallar, usar lista vacía
                purchase_history = []
            else:
                purchase_history = purchases_res.data or []

            # 4. Generar recomendaciones con OpenAI
            try:
                ai_recommendations = openai_service.generate_client_recommendations(
                    client_data, purchase_history
                )
            except Exception as e:
                logger.error("OpenAI recommendation error: %s", e)
                # No fallar, usar fallback
                ai_recommendations = openai_service._fallback_recommendations(
                    client_data.get("churn_score", 0)
                )

            return {
                "client": {
                    "id": client_data["client_id"],
                    "name": client_data.get("name"),
                    "email": client_data.get("email"),
                    "churn_score": int(client_data.get("churn_score") or 0),
                    "segment": client_data.get("segment"),
                    "last_purchase_days": int(client_data.get("last_purchase_days") or 0),
                },
                "recommendations": ai_recommendations,
                "ai_powered": True,
                "purchase_count": len(purchase_history),
            }

        else:
            # Recomendaciones para MÚLTIPLES clientes en riesgo
            
            # 1. Obtener top clientes en riesgo del usuario
            q = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("owner_id", user_id)  # ← SEGURIDAD: Solo clientes del usuario
                .order("churn_score", desc=True)
                .limit(limit)
            )
            
            res = q.execute()
            if getattr(res, "error", None):
                detail = getattr(res.error, "message", str(res.error))
                raise HTTPException(status_code=400, detail=detail)

            items: List[Dict[str, Any]] = []
            
            for client_data in res.data or []:
                # 2. Obtener historial limitado para cada cliente
                purchases_q = (
                    supabase.table("purchases")
                    .select("*, items(*)")
                    .eq("client_id", client_data["client_id"])
                    .eq("owner_id", user_id)  # ← SEGURIDAD
                    .order("purchased_at", desc=True)
                    .limit(5)  # Menos para múltiples clientes
                )
                
                purchases_res = purchases_q.execute()
                if getattr(purchases_res, "error", None):
                    purchase_history = []
                else:
                    purchase_history = purchases_res.data or []
                
                # 3. Generar recomendaciones
                try:
                    ai_recommendations = openai_service.generate_client_recommendations(
                        client_data, purchase_history
                    )
                except Exception as e:
                    logger.error("OpenAI recommendation error for client %s: %s", 
                               client_data["client_id"], e)
                    ai_recommendations = openai_service._fallback_recommendations(
                        client_data.get("churn_score", 0)
                    )

                items.append({
                    "client": {
                        "id": client_data["client_id"],
                        "name": client_data.get("name"),
                        "email": client_data.get("email"),
                        "churn_score": int(client_data.get("churn_score") or 0),
                        "segment": client_data.get("segment"),
                        "last_purchase_days": int(client_data.get("last_purchase_days") or 0),
                    },
                    "recommendations": ai_recommendations,
                    "ai_powered": True,
                    "purchase_count": len(purchase_history),
                })

            return {"items": items, "total": len(items)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/ai/recommendations] error: %s", repr(e))
        raise HTTPException(
            status_code=500, 
            detail="No se pudieron calcular recomendaciones"
        )


@router.get(
    "/clients/{client_id}/suggestions",
    summary="Sugerencias IA personalizadas con OpenAI",
    tags=["ai"],
)
def client_suggestions(
    client_id: Union[str, int],
    user_id: str = Depends(require_user),  # ← AÑADIDO: Autenticación
) -> Dict[str, Any]:
    """
    Genera sugerencias personalizadas usando OpenAI basadas en el historial completo del cliente.
    """
    try:
        # 1. Verificar que el cliente pertenece al usuario
        client_q = (
            supabase.table("clients")
            .select("*")
            .eq("id", client_id)
            .eq("owner_id", user_id)  # ← SEGURIDAD
            .single()
        )
        
        client_res = client_q.execute()
        if getattr(client_res, "error", None):
            detail = getattr(client_res.error, "message", str(client_res.error))
            raise HTTPException(status_code=400, detail=detail)
            
        if not client_res.data:
            raise HTTPException(
                status_code=404, 
                detail="Cliente no encontrado o no pertenece a tu cuenta"
            )
            
        client_data = client_res.data

        # 2. Obtener historial de compras completo
        purchases_q = (
            supabase.table("purchases")
            .select("*, items(*)")
            .eq("client_id", client_id)
            .eq("owner_id", user_id)  # ← SEGURIDAD
            .order("purchased_at", desc=True)
            .limit(20)
        )
        
        purchases_res = purchases_q.execute()
        if getattr(purchases_res, "error", None):
            detail = getattr(purchases_res.error, "message", str(purchases_res.error))
            logger.warning(f"Error obteniendo compras: {detail}")
            purchase_history = []
        else:
            purchase_history = purchases_res.data or []

        # 3. Obtener datos de churn
        churn_res = (
            supabase.table("v_churn_risk")
            .select("*")
            .eq("client_id", client_id)
            .eq("owner_id", user_id)  # ← SEGURIDAD
            .single()
            .execute()
        )
        
        if getattr(churn_res, "error", None):
            logger.warning("No se pudieron obtener datos de churn")
            churn_data = {}
        else:
            churn_data = churn_res.data or {}
            
        churn_score = int(churn_data.get("churn_score") or 0)
        last_purchase_days = int(churn_data.get("last_purchase_days") or 0)
        top_item_id = churn_data.get("top_item_id")

        # 4. Generar sugerencias con OpenAI
        try:
            suggestions = openai_service.generate_client_suggestions(
                client_data, purchase_history, last_purchase_days
            )
        except Exception as e:
            logger.error("OpenAI suggestion error: %s", e)
            suggestions = openai_service._fallback_suggestions()

        return {
            "client_id": client_id,
            "client_name": client_data.get("name"),
            "churn_score": churn_score,
            "last_purchase_days": last_purchase_days,
            "top_item_id": top_item_id,
            "total_purchases": len(purchase_history),
            "suggestions": suggestions,
            "ai_powered": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/ai/clients/{client_id}/suggestions] error: %s", repr(e))
        raise HTTPException(
            status_code=500, 
            detail="No se pudieron calcular sugerencias"
        )


@router.post("/analyze-sentiment", summary="Análisis de sentimiento con OpenAI", tags=["ai"])
def analyze_sentiment(
    payload: Dict[str, str],
    user_id: str = Depends(require_user),  # ← AÑADIDO: Autenticación
) -> Dict[str, Any]:
    """
    Analiza el sentimiento de un texto usando OpenAI.
    Payload: {"text": "texto a analizar"}
    """
    try:
        text = payload.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="El campo 'text' es requerido")
        
        if len(text) > 2000:  # Límite razonable
            raise HTTPException(status_code=400, detail="Texto demasiado largo (máximo 2000 caracteres)")
        
        result = openai_service.analyze_sentiment(text)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[/ai/analyze-sentiment] error: %s", repr(e))
        raise HTTPException(
            status_code=500, 
            detail="No se pudo analizar el sentimiento"
        )


@router.get("/status", summary="Estado del servicio de IA", tags=["ai"])
def ai_status() -> Dict[str, Any]:
    """
    Devuelve el estado del servicio de OpenAI.
    """
    return {
        "openai_available": openai_service._is_available(),
        "service": "OpenAI GPT",
        "model": getattr(openai_service, "_model", "gpt-4o-mini"),
        "features": [
            "client_recommendations",
            "client_suggestions", 
            "sentiment_analysis"
        ]
    }
