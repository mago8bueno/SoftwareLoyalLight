# backend/app/api/ai.py
# === Recomendaciones IA con fallbacks y compatibilidad /suggestions ===
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import logging

from app.db.supabase import supabase
from app.utils.auth import require_user

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

# --------- Inicialización segura del servicio de IA ---------
try:
    from app.services.openai_service import OpenAIService
    openai_service = OpenAIService()
    logger.info("✅ OpenAIService inicializado")
except Exception as e:
    logger.error(f"❌ No se pudo inicializar OpenAIService: {e}")
    openai_service = None


# ========================= Helpers =========================
def _safe_single(table: str, **filters) -> Dict[str, Any]:
    """Consulta .single() segura; devuelve {} si falla o no hay datos."""
    try:
        q = supabase.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        res = q.single().execute()
        return res.data or {}
    except Exception as e:
        logger.warning(f"[SUPABASE single] {table} {filters} → {e}")
        return {}

def _safe_list(table: str, limit: int = 10, order: Optional[Tuple[str, bool]] = None, **filters) -> List[Dict[str, Any]]:
    """Consulta múltiple segura; devuelve [] si falla."""
    try:
        q = supabase.table(table).select("*")
        for k, v in filters.items():
            q = q.eq(k, v)
        if order:
            col, desc = order
            q = q.order(col, desc=desc)
        if limit:
            q = q.limit(limit)
        res = q.execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"[SUPABASE list] {table} {filters} → {e}")
        return []

def _risk_label(score: Optional[float]) -> str:
    """Mapea score 0–1 a etiqueta de riesgo."""
    if score is None:
        return "desconocido"
    try:
        s = float(score)
    except Exception:
        return "desconocido"
    if s >= 0.7:
        return "alto"
    if s >= 0.4:
        return "medio"
    return "bajo"

def _rule_based_actions(name: str, risk_label: str) -> List[str]:
    """Sugerencias deterministas si la IA no está disponible."""
    base = name or "el cliente"
    if risk_label == "alto":
        return [
            f"Lanzar cupón de recuperación 20–30% para {base} válido 72h.",
            "Mensaje 1:1 por WhatsApp/DM con foto del nuevo drop y CTA directo.",
            "Ofrecer envío gratis si añade ≥ 2 productos al carrito.",
            "Reactivar con bundle personalizado (top + bottom) con anclaje de precio.",
        ]
    if risk_label == "medio":
        return [
            "Email con recomendaciones basadas en compras previas + stock limitado.",
            "Cross-sell: sugerir accesorios que combinan con su última compra.",
            "Incentivo suave (10% o puntos dobles) con caducidad a 7 días.",
        ]
    # bajo o desconocido
    return [
        "Programa de referidos: 10% para ambos en su próxima compra.",
        "Upsell a versión premium/colorway exclusivo en próxima visita.",
        "Contenido UGC: pedir foto con look + repost; recompensa puntos.",
    ]

def _client_basic(client_id: Union[str, int], user_id: str) -> Dict[str, Any]:
    """Verifica pertenencia y obtiene datos mínimos del cliente."""
    client = _safe_single("clients", id=client_id, owner_id=user_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o no pertenece a tu cuenta")
    return {
        "id": client.get("id"),
        "name": client.get("name") or "",
        "email": client.get("email") or client.get("phone") or "",
        "owner_id": client.get("owner_id"),
    }

def _client_metrics(client_id: Union[str, int], user_id: str) -> Dict[str, Any]:
    """Recoge métricas si existen; tolera ausencia de vistas/tablas."""
    # v_churn_risk: {client_id, owner_id, risk_score, last_order_at, orders_count, avg_ticket, ltv}
    churn = _safe_single("v_churn_risk", client_id=client_id, owner_id=user_id)
    # orders (opcional) para último pedido si la vista no está
    if not churn:
        orders = _safe_list("orders", limit=1, order=("created_at", True), owner_id=user_id, client_id=client_id)
        last_order_at = orders[0]["created_at"] if orders else None
    else:
        last_order_at = churn.get("last_order_at")

    metrics = {
        "risk_score": churn.get("risk_score"),
        "risk_label": _risk_label(churn.get("risk_score")),
        "orders_count": churn.get("orders_count"),
        "avg_ticket": churn.get("avg_ticket"),
        "ltv": churn.get("ltv"),
        "last_order_at": last_order_at,
    }
    return metrics

def _get_ai_recommendations(client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> List[str]:
    """Obtiene recomendaciones usando OpenAI si está disponible."""
    if openai_service is None:
        return []
    
    try:
        # Preparar datos del cliente para OpenAI
        ai_client_data = {
            "id": client_data.get("id"),
            "name": client_data.get("name"),
            "email": client_data.get("email"),
            "churn_score": client_data.get("risk_score", 0) * 100 if client_data.get("risk_score") else 0,
            "segment": "general",
            "ltv": client_data.get("ltv", 0),
            "last_purchase_days": 30  # valor por defecto
        }
        
        # Llamar al servicio de OpenAI
        recommendations = openai_service.generate_client_recommendations(
            ai_client_data, 
            purchase_history
        )
        
        # Extraer descripciones de las recomendaciones
        actions = []
        for rec in recommendations:
            if isinstance(rec, dict) and "description" in rec:
                actions.append(rec["description"])
            elif isinstance(rec, str):
                actions.append(rec)
        
        return actions[:5]  # Máximo 5 acciones
        
    except Exception as e:
        logger.warning(f"[OpenAI] Error generando recomendaciones: {e}")
        return []

def _compose_item(basic: Dict[str, Any], m: Dict[str, Any], store_kind: str = "retail moda") -> Dict[str, Any]:
    """Arma la ficha de recomendaciones para un cliente."""
    
    # Intentar obtener recomendaciones de IA
    ai_actions = []
    if openai_service is not None:
        try:
            # Preparar historial de compras (vacío por ahora)
            purchase_history = []
            
            # Preparar datos del cliente con métricas
            client_data_with_metrics = {**basic, **m}
            
            ai_actions = _get_ai_recommendations(client_data_with_metrics, purchase_history)
        except Exception as e:
            logger.warning(f"Error obteniendo recomendaciones IA: {e}")
    
    # Si tenemos recomendaciones de IA, usarlas
    if ai_actions:
        actions = ai_actions
        note = "Recomendaciones generadas por IA"
        source = "llm"
    else:
        # Fallback a reglas deterministas
        actions = _rule_based_actions(basic.get("name", ""), m.get("risk_label"))
        note = "Fallback determinista por indisponibilidad de IA o datos insuficientes."
        source = "rules"
    
    return {
        "client_id": basic.get("id"),
        "client_name": basic.get("name"),
        "risk_score": m.get("risk_score"),
        "risk_label": m.get("risk_label"),
        "last_order_at": m.get("last_order_at"),
        "actions": actions,
        "note": note,
        "source": source,
    }


# ========================= Endpoints =========================
@router.get("/recommendations", summary="Recomendaciones IA (alias de /suggestions)")
@router.get("/suggestions", summary="Recomendaciones IA")
def get_suggestions(
    client_id: Optional[Union[str, int]] = Query(
        None, description="ID de cliente; si no se pasa, devuelve top clientes en riesgo"
    ),
    limit: int = Query(5, ge=1, le=50),
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    - Si llega `client_id`: devuelve recomendaciones para ese cliente.
    - Si no: devuelve un listado de `limit` clientes en mayor riesgo con acciones para cada uno.
    Nunca lanza 500: retorna estructura con `error` y `fallback` si algo falla.
    """
    try:
        logger.info(f"🚀 /ai/suggestions user={user_id} client_id={client_id} limit={limit}")

        # --- Caso 1: cliente concreto ---
        if client_id is not None:
            basic = _client_basic(client_id, user_id)
            metrics = _client_metrics(client_id, user_id)
            item = _compose_item(basic, metrics)
            return {
                "error": None,
                "fallback": item["source"] != "llm",
                "items": [item],
            }

        # --- Caso 2: top clientes en riesgo ---
        # Preferimos vista v_churn_risk si existe
        risk_rows = _safe_list(
            "v_churn_risk",
            limit=limit,
            order=("risk_score", True),
            owner_id=user_id,
        )

        items: List[Dict[str, Any]] = []
        if risk_rows:
            for row in risk_rows:
                cid = row.get("client_id")
                if not cid:
                    continue
                try:
                    basic = _client_basic(cid, user_id)
                except HTTPException:
                    continue
                m = {
                    "risk_score": row.get("risk_score"),
                    "risk_label": _risk_label(row.get("risk_score")),
                    "orders_count": row.get("orders_count"),
                    "avg_ticket": row.get("avg_ticket"),
                    "ltv": row.get("ltv"),
                    "last_order_at": row.get("last_order_at"),
                }
                items.append(_compose_item(basic, m))
        else:
            # Fallback: toma clientes "activos" o simplemente los primeros
            clients = _safe_list("clients", limit=limit, owner_id=user_id)
            for c in clients:
                basic = {
                    "id": c.get("id"),
                    "name": c.get("name") or "",
                    "email": c.get("email") or c.get("phone") or "",
                    "owner_id": c.get("owner_id"),
                }
                m = {
                    "risk_score": None,
                    "risk_label": "desconocido",
                    "orders_count": None,
                    "avg_ticket": None,
                    "ltv": None,
                    "last_order_at": None,
                }
                items.append(_compose_item(basic, m))

        return {
            "error": None,
            "fallback": any(i["source"] != "llm" for i in items),
            "items": items,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error crítico en /ai/suggestions: {repr(e)}")
        return {
            "error": "No se pudieron generar recomendaciones",
            "fallback": True,
            "items": [],
            "debug_info": {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "service_available": openai_service is not None,
            },
        }

@router.get("/status", summary="Estado del servicio de IA")
def ai_status(user_id: str = Depends(require_user)) -> Dict[str, Any]:
    """
    Endpoint para verificar el estado del servicio de IA.
    """
    try:
        status = {
            "openai_available": openai_service is not None,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
        }
        
        if openai_service is not None:
            try:
                # Intentar obtener el status del servicio
                if hasattr(openai_service, 'get_status'):
                    ai_status_info = openai_service.get_status()
                    status.update(ai_status_info)
                else:
                    status["features"] = ["recommendations", "suggestions"]
                    status["model"] = "gpt-4o-mini"
            except Exception as e:
                status["openai_error"] = str(e)
        
        return status
        
    except Exception as e:
        logger.error(f"Error en /ai/status: {e}")
        return {
            "openai_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

@router.post("/test-recommendation", summary="Prueba de recomendación para un cliente")
def test_recommendation(
    payload: Dict[str, Any],
    user_id: str = Depends(require_user),
) -> Dict[str, Any]:
    """
    Endpoint de prueba para generar recomendaciones con datos personalizados.
    
    Ejemplo de payload:
    {
        "client_name": "Ana García",
        "risk_score": 0.7,
        "last_purchase_days": 45
    }
    """
    try:
        # Datos básicos del cliente
        basic = {
            "id": "test-client-id",
            "name": payload.get("client_name", "Cliente de Prueba"),
            "email": "test@example.com",
            "owner_id": user_id,
        }
        
        # Métricas simuladas
        metrics = {
            "risk_score": payload.get("risk_score", 0.5),
            "risk_label": _risk_label(payload.get("risk_score", 0.5)),
            "orders_count": payload.get("orders_count", 3),
            "avg_ticket": payload.get("avg_ticket", 50.0),
            "ltv": payload.get("ltv", 150.0),
            "last_order_at": None,
        }
        
        # Generar recomendación
        item = _compose_item(basic, metrics)
        
        return {
            "success": True,
            "recommendation": item,
            "openai_used": item["source"] == "llm",
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error en test-recommendation: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
