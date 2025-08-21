# backend/app/api/ai.py
# === Recomendaciones IA con fallbacks y compatibilidad /suggestions ===
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import logging

from app.db.supabase import supabase
from app.services.openai_service import OpenAIService
from app.utils.auth import require_user

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

# --------- Inicialización segura del servicio de IA ---------
try:
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

def _build_prompt_single(store_kind: str, basic: Dict[str, Any], m: Dict[str, Any]) -> str:
    """Prompt compacto para 3–6 sugerencias accionables."""
    last_dt = m.get("last_order_at")
    last_str = ""
    if last_dt:
        try:
            last_str = datetime.fromisoformat(str(last_dt).replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            last_str = str(last_dt)
    return f"""
Eres un asesor de growth para una tienda de ropa ({store_kind}). Hablas en español y das acciones concretas.
Cliente: {basic.get('name') or 'N/D'} (ID {basic.get('id')})
Métricas: risk_score={m.get('risk_score')}, risk_label={m.get('risk_label')}, orders_count={m.get('orders_count')}, avg_ticket={m.get('avg_ticket')}, ltv={m.get('ltv')}, last_order_at={last_str}
Objetivo: 3–6 acciones de recuperación o aumento de valor en formato viñetas breves (≤120 caracteres cada una), específicas y medibles, sin jerga, sin adornos.
No inventes datos; si faltan, asúmelo y propone acciones low-risk.
Sal de forma JSON con `actions: string[]` y `note: string`.
"""

def _ask_llm(prompt: str) -> Dict[str, Any]:
    """Consulta IA si está disponible y devuelve {'actions': [...], 'note': '...'} o {}."""
    if openai_service is None:
        return {}
    try:
        # Asumimos un método genérico chat(messages, temperature=0.2, max_tokens=400)
        messages = [
            {"role": "system", "content": "Eres un asesor frío y técnico. Responde solo con JSON válido."},
            {"role": "user", "content": prompt},
        ]
        text = openai_service.chat(messages=messages, temperature=0.2, max_tokens=500)
        # Intento de parseo seguro
        import json
        data = json.loads(text)
        if isinstance(data, dict) and "actions" in data:
            # normaliza
            actions = [a for a in data.get("actions", []) if isinstance(a, str)]
            note = data.get("note") if isinstance(data.get("note"), str) else ""
            return {"actions": actions, "note": note}
    except Exception as e:
        logger.warning(f"[LLM] fallo parseando/consultando: {e}")
    return {}

def _compose_item(basic: Dict[str, Any], m: Dict[str, Any], store_kind: str = "retail moda") -> Dict[str, Any]:
    """Arma la ficha de recomendaciones para un cliente."""
    prompt = _build_prompt_single(store_kind, basic, m)
    llm = _ask_llm(prompt)
    if llm:
        actions = llm["actions"]
        note = llm.get("note", "")
    else:
        actions = _rule_based_actions(basic.get("name", ""), m.get("risk_label"))
        note = "Fallback determinista por indisponibilidad de IA o datos insuficientes."
    return {
        "client_id": basic.get("id"),
        "client_name": basic.get("name"),
        "risk_score": m.get("risk_score"),
        "risk_label": m.get("risk_label"),
        "last_order_at": m.get("last_order_at"),
        "actions": actions,
        "note": note,
        "source": "llm" if llm else "rules",
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
            # Fallback: toma clientes “activos” o simplemente los primeros
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
