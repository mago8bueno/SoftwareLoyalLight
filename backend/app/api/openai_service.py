# backend/app/services/openai_service.py
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

# Ajusta según tu estructura real
from app.core.settings import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Servicio para generar recomendaciones, sugerencias y análisis de sentimiento
    apoyado en OpenAI. Incluye parseo robusto de JSON y fallbacks deterministas.
    """

    def __init__(self) -> None:
        """
        Inicializa el cliente con la API key.
        Preferimos OPENAI_API_KEY; si no, caemos a settings.NEXT_PUBLIC_OPENAI_KEY (no recomendado para backend).
        """
        self.client = None  # type: ignore[assignment]

        # 1) Prioriza variable de entorno estándar para backend
        api_key = os.getenv("OPENAI_API_KEY")

        # 2) Fallback a settings (si insistes en usarlo)
        if not api_key:
            api_key = getattr(settings, "OPENAI_API_KEY", None)

        # 3) Fallback adicional por compatibilidad con tu código previo (NO recomendado)
        if not api_key:
            api_key = getattr(settings, "NEXT_PUBLIC_OPENAI_KEY", None)

        if not api_key:
            logger.warning(
                "OpenAI API key no configurada. Funcionalidades de IA deshabilitadas."
            )
            return

        try:
            # SDK moderno (openai>=1.0) → from openai import OpenAI
            # Si usas el SDK viejo, este bloque puede ajustarse al viejo `openai` global.
            from openai import OpenAI  # type: ignore

            self.client = OpenAI(api_key=api_key)
            self._model_recos = "gpt-4o-mini"
            self._model_sentiment = "gpt-4o-mini"
        except Exception as e:
            logger.error(f"No se pudo inicializar OpenAI client: {e}")
            self.client = None

    # -------------------- Utilidades internas --------------------

    def _is_available(self) -> bool:
        """Verifica si OpenAI está disponible."""
        return self.client is not None

    @staticmethod
    def _extract_json(text: str) -> Any:
        """
        Extrae el primer JSON válido (objeto o array) de un texto.
        Soporta casos con explicaciones antes/después del JSON.
        """
        text = text.strip()

        # Intento directo primero
        try:
            return json.loads(text)
        except Exception:
            pass

        # Busca el primer bloque que parezca JSON (array u objeto)
        # Captura balanceada básica: probamos con el primer bloque [] o {}
        patterns = [
            r"(\[.*\])",
            r"(\{.*\})",
        ]
        for pat in patterns:
            match = re.search(pat, text, flags=re.DOTALL)
            if match:
                candidate = match.group(1)
                try:
                    return json.loads(candidate)
                except Exception:
                    continue

        # Si no se puede parsear, lanzamos error
        raise json.JSONDecodeError("No se encontró JSON válido en la respuesta.", text, 0)

    @staticmethod
    def _ensure_list(payload: Any) -> List[Dict[str, Any]]:
        """
        Normaliza para devolver siempre List[Dict].
        - Si es dict -> [dict]
        - Si es list -> lo valida superficialmente
        - Si no, excepción
        """
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            # Validación suave: cada elemento debe ser dict
            cleaned: List[Dict[str, Any]] = []
            for i, item in enumerate(payload):
                if not isinstance(item, dict):
                    # Intento de conversión si viene como string JSON en elementos
                    if isinstance(item, str):
                        try:
                            item = json.loads(item)
                        except Exception:
                            raise ValueError(f"Elemento {i} no es un dict ni JSON válido.")
                if not isinstance(item, dict):
                    raise ValueError(f"Elemento {i} no es un dict.")
                cleaned.append(item)
            return cleaned
        raise ValueError("La respuesta JSON no es ni lista ni objeto.")

    @staticmethod
    def _prepare_client_context(client_data: Dict[str, Any],
                                purchase_history: List[Dict[str, Any]]) -> str:
        """
        Compacta la info del cliente de manera estable y legible para el prompt.
        """
        # Selecciona campos clave con defaults
        cid = client_data.get("id") or client_data.get("client_id") or "desconocido"
        name = client_data.get("name") or client_data.get("full_name") or "N/D"
        email = client_data.get("email") or "N/D"
        churn = client_data.get("churn_score", 0)
        segment = client_data.get("segment") or "general"
        ltv = client_data.get("ltv", 0)
        last_category = client_data.get("last_category") or "N/D"
        fav_colors = client_data.get("favorite_colors") or []
        fav_sizes = client_data.get("sizes") or client_data.get("favorite_sizes") or []

        # Historial resumido
        last_orders = []
        for p in (purchase_history or [])[:25]:
            last_orders.append({
                "date": p.get("date"),
                "sku": p.get("sku"),
                "category": p.get("category"),
                "price": p.get("price"),
                "discount": p.get("discount"),
                "channel": p.get("channel"),
                "returned": bool(p.get("returned", False)),
            })

        context = {
            "client_id": cid,
            "name": name,
            "email": email,
            "segment": segment,
            "churn_score": churn,
            "ltv": ltv,
            "last_known_category": last_category,
            "favorite_colors": fav_colors,
            "favorite_sizes": fav_sizes,
            "recent_purchases": last_orders,
        }
        return json.dumps(context, ensure_ascii=False)

    @staticmethod
    def _prepare_detailed_context(client_data: Dict[str, Any],
                                  purchase_history: List[Dict[str, Any]],
                                  days_since_last: int) -> str:
        """
        Contexto enriquecido para sugerencias: añade recencia, ticket medio, etc.
        """
        # Ticket medio
        prices = [p.get("price", 0) or 0 for p in (purchase_history or []) if isinstance(p.get("price", 0), (int, float))]
        avg_ticket = round(sum(prices) / len(prices), 2) if prices else 0.0

        # Categorías más frecuentes (top-3)
        freq: Dict[str, int] = {}
        for p in (purchase_history or []):
            cat = (p.get("category") or "N/D").lower()
            freq[cat] = freq.get(cat, 0) + 1
        top_cats = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]

        rich = {
            "base": json.loads(OpenAIService._prepare_client_context(client_data, purchase_history)),
            "metrics": {
                "days_since_last_purchase": days_since_last,
                "avg_ticket": avg_ticket,
                "top_categories": top_cats,
                "orders_count": len(purchase_history or []),
            },
        }
        return json.dumps(rich, ensure_ascii=False)

    @staticmethod
    def _fallback_recommendations(churn_score: float | int) -> List[Dict[str, Any]]:
        """
        Fallback determinista según churn_score.
        """
        risk = float(churn_score or 0)
        if risk >= 0.7:
            urgency = "alta"
        elif risk >= 0.4:
            urgency = "media"
        else:
            urgency = "media"

        return [
            {
                "type": "discount",
                "description": "Cupón del 15% en su categoría favorita, válido 7 días.",
                "urgency": urgency,
                "channel": "email",
                "reasoning": "Incentiva recompra rápida en categoría de interés."
            },
            {
                "type": "personal_message",
                "description": "Mensaje personalizado con recomendaciones basadas en su historial.",
                "urgency": "media",
                "channel": "whatsapp",
                "reasoning": "Eleva la relevancia percibida y la tasa de clic."
            },
            {
                "type": "loyalty_nudge",
                "description": "Recordatorio de puntos acumulados y recompensa al siguiente nivel.",
                "urgency": "media",
                "channel": "sms",
                "reasoning": "Refuerza el valor del programa y el retorno a tienda."
            },
        ]

    @staticmethod
    def _fallback_suggestions() -> List[Dict[str, Any]]:
        """
        Fallback determinista para sugerencias.
        """
        return [
            {
                "type": "product_recommendation",
                "title": "Pack básico de temporada",
                "description": "Combina 1 prenda superior + 1 inferior con 10% extra al comprar ambas.",
                "priority": "alta",
                "expected_impact": "Incremento del ticket medio en un 10–15%."
            },
            {
                "type": "engagement_action",
                "title": "Quiz de estilo en 30s",
                "description": "Encuesta rápida para perfilar gustos y mejorar recomendaciones.",
                "priority": "media",
                "expected_impact": "Aumento de CTR y afinación del perfilado."
            }
        ]

    # -------------------- Funcionalidades públicas --------------------

    def generate_client_recommendations(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Genera recomendaciones personalizadas para un cliente.
        Devuelve siempre una lista de dicts.
        """
        if not self._is_available():
            return self._fallback_recommendations(client_data.get("churn_score", 0))

        try:
            client_context = self._prepare_client_context(client_data, purchase_history)
            user_prompt = f"""
Eres un experto en marketing y fidelización de clientes para una tienda de ropa.

DATOS DEL CLIENTE:
{client_context}

TAREA:
Genera 3–5 recomendaciones específicas y accionables para retener/reactivar a este cliente.
Cada recomendación debe incluir:
1. type (por ejemplo: "discount", "personal_message", "loyalty_nudge", "call")
2. description (concreto y accionable)
3. urgency ("alta" | "media" | "baja")
4. channel (email | sms | whatsapp | llamada | app)
5. reasoning (breve justificación)

Responde SOLO con un JSON válido (array de objetos).
"""
            # SDK moderno: responses.create con messages
            resp = self.client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._model_recos,
                messages=[
                    {"role": "system", "content": "Eres un experto en marketing de retail y fidelización."},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=800,
                temperature=0.6,
            )

            content = (resp.choices[0].message.content or "").strip()
            payload = self._extract_json(content)
            recos = self._ensure_list(payload)
            return recos

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de OpenAI (recomendaciones): {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))
        except Exception as e:
            logger.error(f"Error generando recomendaciones con OpenAI: {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))

    def generate_client_suggestions(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
        days_since_last: int
    ) -> List[Dict[str, Any]]:
        """
        Genera 2–4 sugerencias personalizadas para mejorar experiencia y ventas.
        """
        if not self._is_available():
            return self._fallback_suggestions()

        try:
            context = self._prepare_detailed_context(client_data, purchase_history, days_since_last)
            user_prompt = f"""
Eres un consultor de experiencia del cliente para una tienda de ropa.

PERFIL DEL CLIENTE (JSON):
{context}

TAREA:
Genera 2–4 sugerencias personalizadas centradas en:
- productos concretos o categorías probables,
- ofertas personalizadas (pack, cross-sell, upsell),
- acciones de engagement (quiz, early access, etc.).

Responde SOLO con un JSON válido (array), con cada elemento:
{{
  "type": "product_recommendation|engagement_action|offer",
  "title": "Título breve",
  "description": "Descripción detallada y accionable",
  "priority": "alta|media|baja",
  "expected_impact": "Impacto esperado cuantitativo o cualitativo"
}}
"""
            resp = self.client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._model_recos,
                messages=[
                    {"role": "system", "content": "Eres un experto en personalización de experiencias de compra."},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=700,
                temperature=0.7,
            )

            content = (resp.choices[0].message.content or "").strip()
            payload = self._extract_json(content)
            suggestions = self._ensure_list(payload)
            return suggestions

        except Exception as e:
            logger.error(f"Error generando sugerencias con OpenAI: {e}")
            return self._fallback_suggestions()

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analiza el sentimiento de un texto. Devuelve dict con sentiment, confidence, emotions, key_phrases, ai_powered.
        """
        if not self._is_available():
            return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "key_phrases": [], "ai_powered": False}

        try:
            user_prompt = f"""
Analiza el sentimiento del siguiente texto y responde SOLO con un JSON VÁLIDO.

TEXTO: {json.dumps(text, ensure_ascii=False)}

Formato:
{{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.xx,
  "emotions": ["joy","trust","anger","fear","surprise","sadness"],
  "key_phrases": ["...","..."]
}}
"""
            resp = self.client.chat.completions.create(  # type: ignore[attr-defined]
                model=self._model_sentiment,
                messages=[
                    {"role": "system", "content": "Eres un analista experto en NLP y sentimiento."},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=350,
                temperature=0.2,
            )

            content = (resp.choices[0].message.content or "").strip()
            payload = self._extract_json(content)

            if not isinstance(payload, dict):
                raise ValueError("La respuesta de sentimiento no es un objeto JSON.")

            # Normaliza campos mínimos
            sentiment = payload.get("sentiment", "neutral")
            confidence = float(payload.get("confidence", 0.5))
            emotions = payload.get("emotions") or []
            key_phrases = payload.get("key_phrases") or []

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "emotions": emotions,
                "key_phrases": key_phrases,
                "ai_powered": True,
            }

        except Exception as e:
            logger.error(f"Error analizando sentimiento con OpenAI: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "key_phrases": [], "ai_powered": False}
