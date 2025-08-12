# backend/app/services/openai_service.py
import json
import logging
from typing import Any, Dict, List

import openai

from app.core.settings import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self) -> None:
        """Initialize OpenAI client using env API key."""
        self.client = None
        if settings.NEXT_PUBLIC_OPENAI_KEY:
            openai.api_key = settings.NEXT_PUBLIC_OPENAI_KEY
            self.client = openai
        else:
            logger.warning("OpenAI API key not configured. AI features disabled.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _is_available(self) -> bool:
        return self.client is not None and settings.NEXT_PUBLIC_OPENAI_KEY is not None

    def _prepare_client_context(
        self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]
    ) -> str:
        context = (
            f"Cliente ID: {client_data.get('client_id','N/A')}\n"
            f"Nombre: {client_data.get('name','N/A')}\n"
            f"Email: {client_data.get('email','N/A')}\n"
            f"Puntuación de riesgo de abandono: {client_data.get('churn_score',0)}/100\n"
        )
        if purchase_history:
            context += f"\nHistorial de compras ({len(purchase_history)} compras recientes):\n"
            for i, p in enumerate(purchase_history[:5], 1):
                total = p.get("total", 0)
                date = p.get("created_at", "N/A")
                items_count = len(p.get("items", []))
                context += (
                    f"  {i}. Fecha: {date}, Total: ${total}, Productos: {items_count}\n"
                )
                for item in p.get("items", [])[:3]:
                    item_name = item.get("name", "Producto sin nombre")
                    item_price = item.get("price", 0)
                    context += f"     - {item_name}: ${item_price}\n"
        else:
            context += "\nSin historial de compras registrado."

        if "last_purchase_date" in client_data:
            context += f"\nÚltima compra: {client_data['last_purchase_date']}"
        if "total_spent" in client_data:
            context += f"\nTotal gastado: ${client_data['total_spent']}"
        return context

    def _fallback_suggestions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "product_recommendation",
                "title": "Productos populares",
                "description": "Mostrar productos más vendidos de la temporada",
                "priority": "media",
                "expected_impact": "Incremento en ventas del 5-10%",
            },
            {
                "type": "seasonal_offer",
                "title": "Oferta estacional",
                "description": "Descuento en productos de temporada",
                "priority": "alta",
                "expected_impact": "Reactivación de cliente inactivo",
            },
        ]

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #
    def generate_client_suggestions(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
        days_since_last: int,
    ) -> List[Dict[str, Any]]:
        """Return sanitized suggestions (title/description always present)."""
        if not self._is_available():
            return self._fallback_suggestions()

        try:
            context = self._prepare_client_context(client_data, purchase_history)
            prompt = f"""
Eres un consultor de experiencia del cliente para una tienda de ropa.

PERFIL DEL CLIENTE:
{context}
Días desde última compra: {days_since_last}

TAREA:
Genera 2-4 sugerencias personalizadas para mejorar la experiencia y aumentar las ventas.
Responde SOLO con un JSON en este formato:
[
  {{
    "type": "product_recommendation",
    "title": "Título de la sugerencia",
    "description": "Descripción detallada",
    "priority": "alta",
    "expected_impact": "Impacto esperado"
  }}
]
"""
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en personalización de experiencias de compra.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                temperature=0.8,
            )

            raw_suggestions = json.loads(
                response.choices[0].message.content.strip()
            )
            sanitized: List[Dict[str, Any]] = []
            for s in raw_suggestions:
                title = (s.get("title") or "").strip()
                desc = (s.get("description") or "").strip()
                if not desc:
                    # Replace with fallback suggestion
                    fallback = {
                        "type": "engagement",
                        "title": "Recontactar",
                        "description": "Ofrecer un cupón del 10% para reactivar al cliente",
                        "priority": "media",
                        "expected_impact": "Incremento de recompras",
                    }
                    sanitized.append(fallback)
                    logger.warning(
                        "Missing description in AI suggestion; using fallback: %s", s
                    )
                    continue
                sug: Dict[str, Any] = {"type": s.get("type", "insight"), "description": desc}
                if title:
                    sug["title"] = title
                if s.get("priority"):
                    sug["priority"] = s["priority"]
                if s.get("expected_impact"):
                    sug["expected_impact"] = s["expected_impact"]
                sanitized.append(sug)

            return sanitized

        except Exception as e:
            logger.error(f"Error generating suggestions with OpenAI: {e}")
            return self._fallback_suggestions()
