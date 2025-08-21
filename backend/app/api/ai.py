# backend/app/api/ai.py - VERSIÓN COMPLETA CORREGIDA
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional, Union
from app.db.supabase import supabase
from app.services.openai_service import OpenAIService
from app.utils.auth import require_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Inicializar servicio con manejo de errores
try:
    openai_service = OpenAIService()
    logger.info("✅ OpenAI service inicializado")
except Exception as e:
    logger.error(f"❌ Error inicializando OpenAI service: {e}")
    openai_service = None


@router.get("/recommendations", summary="Recomendaciones IA ultra-robustas", tags=["ai"])
def recommendations(
    client_id: Optional[Union[str, int]] = Query(
        None, description="ID de cliente (opcional; admite UUID o entero)"
    ),
    limit: int = Query(5, ge=1, le=50),
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Genera recomendaciones usando IA con múltiples fallbacks y manejo robusto de errores.
    """
    try:
        logger.info(f"🚀 Iniciando recomendaciones IA - User: {user_id}, Client: {client_id}")
        
        if client_id is not None:
            # RECOMENDACIONES PARA UN CLIENTE ESPECÍFICO
            return _get_single_client_recommendations(client_id, user_id)
        else:
            # RECOMENDACIONES PARA MÚLTIPLES CLIENTES EN RIESGO
            return _get_multiple_client_recommendations(limit, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error crítico en /ai/recommendations: {repr(e)}")
        # Fallback de emergencia
        return {
            "error": "No se pudieron generar recomendaciones",
            "fallback": True,
            "items": [],
            "debug_info": {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "user_id": user_id,
                "service_available": openai_service is not None if openai_service else False
            }
        }


def _get_single_client_recommendations(client_id: Union[str, int], user_id: str) -> Dict[str, Any]:
    """Obtiene recomendaciones para un cliente específico con manejo robusto."""
    try:
        # 1. Verificar que el cliente pertenece al usuario
        logger.info(f"🔍 Verificando cliente {client_id} para user {user_id}")
        
        client_check = (
            supabase.table("clients")
            .select("owner_id, name, email")
            .eq("id", client_id)
            .eq("owner_id", user_id)
            .single()
            .execute()
        )
        
        if not client_check.data:
            raise HTTPException(
                status_code=404, 
                detail="Cliente no encontrado o no pertenece a tu cuenta"
            )
        
        client_basic_data = client_check.data
        logger.info(f"✅ Cliente verificado: {client_basic_data.get('name', 'Sin nombre')}")

        # 2. Obtener datos de churn (puede fallar si no existe la vista)
        churn_data = {}
        try:
            churn_res = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("client_id", client_id)
                .eq("owner_id", user_id)
                .single()
                .execute()
            )
            
            if churn_res.data:
                churn_data = churn_res.data
                logger.info("✅ Datos de churn obtenidos")
            else:
                logger.warning("⚠️  No se encontraron datos de churn")
                
        except Exception as e:
            logger.warning(f"⚠️  Error obteniendo churn data: {e}")
            churn_data = {}

        # 3. Combinar datos del cliente
        combined_client_data = {**client_basic_data, **churn_data}

        # 4. Obtener historial de compras
        purchase_history = _get_purchase_history(client_id, user_id, limit=10)

        # 5. Generar recomendaciones con IA
        recommendations = []
        if openai_service and openai_service._is_available():
            try:
                recommendations = openai_service.generate_client_recommendations(
                    combined_client_data, purchase_history
                )
                logger.info(f"✅ OpenAI generó {len(recommendations)} recomendaciones")
            except Exception as e:
                logger.error(f"❌ Error con OpenAI: {e}")
                recommendations = _fallback_recommendations_single(combined_client_data)
        else:
            logger.warning("⚠️  OpenAI no disponible, usando fallback")
            recommendations = _fallback_recommendations_single(combined_client_data)

        return {
            "client": {
                "id": client_id,
                "name": combined_client_data.get("name"),
                "email": combined_client_data.get("email"),
                "churn_score": int(combined_client_data.get("churn_score", 0) or 0),
                "segment": combined_client_data.get("segment"),
                "last_purchase_days": int(combined_client_data.get("last_purchase_days", 999) or 999),
            },
            "recommendations": recommendations,
            "ai_powered": openai_service._is_available() if openai_service else False,
            "purchase_count": len(purchase_history),
            "generated_at": "2025-01-21T12:00:00Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en recomendaciones single client: {e}")
        raise HTTPException(status_code=500, detail="Error generando recomendaciones")


def _get_multiple_client_recommendations(limit: int, user_id: str) -> Dict[str, Any]:
    """Obtiene recomendaciones para múltiples clientes en riesgo."""
    try:
        logger.info(f"📊 Obteniendo recomendaciones para {limit} clientes")
        
        # 1. Obtener clientes en riesgo
        try:
            clients_res = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("owner_id", user_id)
                .order("churn_score", desc=True)
                .limit(limit)
                .execute()
            )
            clients_data = clients_res.data or []
        except Exception as e:
            logger.warning(f"⚠️  Error obteniendo v_churn_risk: {e}")
            # Fallback: obtener clientes básicos
            clients_res = (
                supabase.table("clients")
                .select("*")
                .eq("owner_id", user_id)
                .limit(limit)
                .execute()
            )
            clients_data = clients_res.data or []

        items = []
        for client_data in clients_data:
            try:
                client_id = client_data.get("id") or client_data.get("client_id")
                
                # Historial limitado para múltiples clientes
                purchase_history = _get_purchase_history(client_id, user_id, limit=5)
                
                # Generar recomendaciones
                recommendations = []
                if openai_service and openai_service._is_available():
                    try:
                        recommendations = openai_service.generate_client_recommendations(
                            client_data, purchase_history
                        )
                    except Exception as e:
                        logger.warning(f"⚠️  OpenAI error para cliente {client_id}: {e}")
                        recommendations = _fallback_recommendations_single(client_data)
                else:
                    recommendations = _fallback_recommendations_single(client_data)

                items.append({
                    "client": {
                        "id": client_id,
                        "name": client_data.get("name"),
                        "email": client_data.get("email"),
                        "churn_score": int(client_data.get("churn_score", 0) or 0),
                        "segment": client_data.get("segment"),
                        "last_purchase_days": int(client_data.get("last_purchase_days", 999) or 999),
                    },
                    "recommendations": recommendations,
                    "ai_powered": openai_service._is_available() if openai_service else False,
                    "purchase_count": len(purchase_history),
                })

            except Exception as e:
                logger.warning(f"⚠️  Error procesando cliente {client_data.get('id')}: {e}")
                continue

        return {
            "items": items, 
            "total": len(items),
            "generated_at": "2025-01-21T12:00:00Z"
        }

    except Exception as e:
        logger.error(f"❌ Error en recomendaciones múltiples: {e}")
        return {"items": [], "total": 0}


@router.get(
    "/clients/{client_id}/suggestions",
    summary="Sugerencias IA personalizadas CORREGIDAS",
    tags=["ai"],
)
def client_suggestions(
    client_id: Union[str, int],
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    🔧 ENDPOINT CORREGIDO - Genera sugerencias personalizadas usando IA.
    Este endpoint estaba causando el error 404.
    """
    try:
        logger.info(f"💡 Generando sugerencias para cliente: {client_id}")
        
        # 1. Verificar que el cliente pertenece al usuario
        client_res = (
            supabase.table("clients")
            .select("*")
            .eq("id", client_id)
            .eq("owner_id", user_id)
            .single()
            .execute()
        )
        
        if not client_res.data:
            raise HTTPException(
                status_code=404, 
                detail="Cliente no encontrado o no pertenece a tu cuenta"
            )
            
        client_data = client_res.data
        logger.info(f"✅ Cliente encontrado: {client_data.get('name')}")

        # 2. Obtener historial de compras completo
        purchase_history = _get_purchase_history(client_id, user_id, limit=20)
        
        # 3. Obtener datos de churn si están disponibles
        churn_data = {}
        try:
            churn_res = (
                supabase.table("v_churn_risk")
                .select("*")
                .eq("client_id", client_id)
                .eq("owner_id", user_id)
                .single()
                .execute()
            )
            
            if churn_res.data:
                churn_data = churn_res.data
                
        except Exception as e:
            logger.warning(f"⚠️  No se pudieron obtener datos de churn: {e}")

        # Combinar datos
        combined_data = {**client_data, **churn_data}
        last_purchase_days = int(churn_data.get("last_purchase_days", 999) or 999)

        # 4. Generar sugerencias con IA
        suggestions = []
        if openai_service and openai_service._is_available():
            try:
                suggestions = openai_service.generate_client_suggestions(
                    combined_data, purchase_history, last_purchase_days
                )
                logger.info(f"✅ OpenAI generó {len(suggestions)} sugerencias")
            except Exception as e:
                logger.error(f"❌ Error con OpenAI suggestions: {e}")
                suggestions = _fallback_suggestions()
        else:
            logger.warning("⚠️  OpenAI no disponible, usando sugerencias fallback")
            suggestions = _fallback_suggestions()

        return {
            "client_id": client_id,
            "client_name": client_data.get("name"),
            "churn_score": int(churn_data.get("churn_score", 0) or 0),
            "last_purchase_days": last_purchase_days,
            "total_purchases": len(purchase_history),
            "suggestions": suggestions,
            "ai_powered": openai_service._is_available() if openai_service else False,
            "generated_at": "2025-01-21T12:00:00Z"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error crítico en suggestions: {repr(e)}")
        raise HTTPException(
            status_code=500, 
            detail="No se pudieron generar sugerencias"
        )


@router.post("/analyze-sentiment", summary="Análisis de sentimiento con OpenAI", tags=["ai"])
def analyze_sentiment(
    payload: Dict[str, str],
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Analiza el sentimiento de un texto usando OpenAI.
    Payload: {"text": "texto a analizar"}
    """
    try:
        text = payload.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="El campo 'text' es requerido")
        
        if len(text) > 2000:
            raise HTTPException(status_code=400, detail="Texto demasiado largo (máximo 2000 caracteres)")
        
        if openai_service and openai_service._is_available():
            result = openai_service.analyze_sentiment(text)
        else:
            result = {
                "sentiment": "neutral",
                "confidence": 0.5,
                "emotions": [],
                "key_phrases": [],
                "ai_powered": False
            }
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en análisis de sentimiento: {repr(e)}")
        raise HTTPException(
            status_code=500, 
            detail="No se pudo analizar el sentimiento"
        )


@router.get("/status", summary="Estado del servicio de IA", tags=["ai"])
def ai_status() -> Dict[str, Any]:
    """
    Devuelve el estado del servicio de IA.
    """
    return {
        "openai_available": openai_service._is_available() if openai_service else False,
        "service": "OpenAI GPT",
        "model": getattr(openai_service, "_model", "gpt-4o-mini") if openai_service else None,
        "features": [
            "client_recommendations",
            "client_suggestions", 
            "sentiment_analysis"
        ],
        "status": "operational" if (openai_service and openai_service._is_available()) else "degraded",
        "fallback_enabled": True
    }


# ===== FUNCIONES AUXILIARES =====

def _get_purchase_history(client_id: Union[str, int], user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene historial de compras de forma robusta."""
    try:
        purchases_res = (
            supabase.table("purchases")
            .select("*, items(*)")
            .eq("client_id", client_id)
            .eq("owner_id", user_id)
            .order("purchased_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        if purchases_res.data:
            logger.info(f"✅ {len(purchases_res.data)} compras encontradas")
            return purchases_res.data
        else:
            logger.info("ℹ️  No se encontraron compras")
            return []
            
    except Exception as e:
        logger.warning(f"⚠️  Error obteniendo historial de compras: {e}")
        return []


def _fallback_recommendations_single(client_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Recomendaciones fallback para un cliente."""
    churn_score = int(client_data.get("churn_score", 0) or 0)
    
    if churn_score >= 70:
        return [
            {
                "type": "urgent_offer",
                "description": "Oferta urgente del 25% en toda la tienda válida por 48 horas",
                "urgency": "alta",
                "channel": "whatsapp",
                "reasoning": "Cliente en riesgo crítico necesita intervención inmediata"
            },
            {
                "type": "personal_contact",
                "description": "Llamada personal para entender sus necesidades actuales",
                "urgency": "alta",
                "channel": "llamada",
                "reasoning": "Contacto directo para reconexión emocional"
            }
        ]
    else:
        return [
            {
                "type": "targeted_discount",
                "description": "Descuento del 15% personalizado en su categoría favorita",
                "urgency": "media",
                "channel": "email",
                "reasoning": "Incentivo relevante basado en historial de compras"
            },
            {
                "type": "loyalty_points",
                "description": "Puntos dobles en su próxima compra + regalo sorpresa",
                "urgency": "media", 
                "channel": "email",
                "reasoning": "Refuerzo del programa de fidelidad"
            }
        ]


def _fallback_suggestions() -> List[Dict[str, Any]]:
    """Sugerencias fallback cuando IA no está disponible."""
    return [
        {
            "type": "product_bundle",
            "title": "Pack personalizado de temporada",
            "description": "Combinar productos de categorías más compradas con descuento del 15%",
            "priority": "alta",
            "expected_impact": "Incremento del 20% en ticket promedio"
        },
        {
            "type": "engagement_survey",
            "title": "Quiz de preferencias en 60 segundos",
            "description": "Encuesta rápida para conocer colores, tallas y estilos preferidos",
            "priority": "media",
            "expected_impact": "Mejora del 25% en precisión de recomendaciones"
        },
        {
            "type": "seasonal_preview",
            "title": "Acceso anticipado nueva colección",
            "description": "Preview exclusivo de nuevos productos antes del lanzamiento público",
            "priority": "media",
            "expected_impact": "Aumento del 30% en engagement y exclusividad percibida"
        }
    ]
