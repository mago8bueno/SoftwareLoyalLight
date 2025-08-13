# backend/app/services/openai_service.py
import openai
from typing import Dict, List, Any, Optional
from app.core.settings import settings
import json
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        """
        Inicializa el servicio de OpenAI con la clave de API desde settings.
        """
        self.client = None
        if settings.NEXT_PUBLIC_OPENAI_KEY:
            openai.api_key = settings.NEXT_PUBLIC_OPENAI_KEY
            self.client = openai
        else:
            logger.warning("OpenAI API key not configured. AI features will be disabled.")

    def _is_available(self) -> bool:
        """Verifica si OpenAI está disponible."""
        return self.client is not None and settings.NEXT_PUBLIC_OPENAI_KEY is not None

    def generate_client_recommendations(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Genera recomendaciones personalizadas para un cliente usando OpenAI.
        """
        if not self._is_available():
            return self._fallback_recommendations(client_data.get("churn_score", 0))

        try:
            # Preparar contexto del cliente
            client_context = self._prepare_client_context(client_data, purchase_history)

            prompt = f"""
Eres un experto en marketing y fidelización de clientes para una tienda de ropa.

DATOS DEL CLIENTE:
{client_context}

TAREA:
Genera 3-5 recomendaciones específicas y accionables para retener/reactivar a este cliente.
Cada recomendación debe incluir:
1. Tipo de acción (email, descuento, llamada, etc.)
2. Descripción específica
3. Urgencia (alta/media/baja)
4. Canal recomendado

Responde SOLO con un JSON válido en este formato:
[
  {{
    "type": "discount",
    "description": "Descripción específica de la acción",
    "urgency": "alta",
    "channel": "email",
    "reasoning": "Por qué esta recomendación es efectiva"
  }}
]
"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un experto en marketing de retail y fidelización de clientes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            # Parsear respuesta JSON
            recommendations_text = response.choices[0].message.content.strip()
            recommendations = json.loads(recommendations_text)

            return recommendations

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAI JSON response: {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))
        except Exception as e:
            logger.error(f"Error generating recommendations with OpenAI: {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))

    def generate_client_suggestions(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
        days_since_last: int
    ) -> List[Dict[str, Any]]:
        """
        Genera sugerencias específicas para un cliente basadas en su comportamiento.
        """
        if not self._is_available():
            return self._fallback_suggestions()

        try:
            # Preparar contexto detallado
            context = self._prepare_detailed_context(client_data, purchase_history, days_since_last)

            prompt = f"""
Eres un consultor de experiencia del cliente para una tienda de ropa.

PERFIL DEL CLIENTE:
{context}

TAREA:
Genera 2-4 sugerencias personalizadas para mejorar la experiencia y aumentar las ventas.
Enfócate en productos específicos, ofertas personalizadas y acciones de engagement.

Responde SOLO con un JSON válido:
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
                    {"role": "system", "content": "Eres un experto en personalización de experiencias de compra."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.8
            )

            suggestions_text = response.choices[0].message.content.strip()
            suggestions = json.loads(suggestions_text)

            cleaned_suggestions = []
            for suggestion in suggestions:
                corrected = False
                if "title" not in suggestion and "text" in suggestion:
                    suggestion["title"] = suggestion.pop("text")
                    corrected = True
                if "description" not in suggestion and "reason" in suggestion:
                    suggestion["description"] = suggestion.pop("reason")
                    corrected = True
                if "title" in suggestion and "description" in suggestion:
                    if corrected:
                        logger.warning(f"Corrected suggestion keys: {suggestion}")
                    cleaned_suggestions.append(suggestion)
                else:
                    logger.warning(f"Discarding invalid suggestion: {suggestion}")

            return cleaned_suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions with OpenAI: {e}")
            return self._fallback_suggestions()

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analiza el sentimiento de un texto usando OpenAI.
        """
        if not self._is_available():
            return {"sentiment": "neutral", "confidence": 0.5, "ai_powered": False}

        try:
            prompt = f"""
Analiza el sentimiento del siguiente texto y responde SOLO con un JSON válido:

TEXTO: "{text}"

Formato de respuesta:
{{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.95,
  "emotions": ["joy", "satisfaction"],
  "key_phrases": ["frase relevante 1", "frase relevante 2"]
}}
"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de sentimientos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            sentiment_text = response.choices[0].message.content.strip()
            sentiment_data = json.loads(sentiment_text)
            sentiment_data["ai_powered"] = True

            return sentiment_data

        except Exception as e:
            logger.error(f"Error analyzing sentiment with OpenAI: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "ai_powered": False}

    def _prepare_client_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """
        Prepara el contexto del cliente para enviar a OpenAI.
        """
        # Información básica del cliente
        context = f"""
Cliente ID: {client_data.get('client_id', 'N/A')}
Nombre: {client_data.get('name', 'N/A')}
Email: {client_data.get('email', 'N/A')}
Puntuación de riesgo de abandono: {client_data.get('churn_score', 0)}/100
"""

        # Historial de compras
        if purchase_history:
            context += f"\nHistorial de compras ({len(purchase_history)} compras recientes):\n"
            for i, purchase in enumerate(purchase_history[:5], 1):
                total = purchase.get('total', 0)
                date = purchase.get('created_at', 'N/A')
                items_count = len(purchase.get('items', []))
                context += f"  {i}. Fecha: {date}, Total: ${total}, Productos: {items_count}\n"

                # Detalles de productos si están disponibles
                for item in purchase.get('items', [])[:3]:  # Solo primeros 3 items
                    item_name = item.get('name', 'Producto sin nombre')
                    item_price = item.get('price', 0)
                    context += f"     - {item_name}: ${item_price}\n"
        else:
            context += "\nSin historial de compras registrado."

        # Métricas adicionales si están disponibles
        if 'last_purchase_date' in client_data:
            context += f"\nÚltima compra: {client_data['last_purchase_date']}"

        if 'total_spent' in client_data:
            context += f"\nTotal gastado: ${client_data['total_spent']}"

        return context

    def _prepare_detailed_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]], days_since_last: int) -> str:
        """
        Prepara un contexto más detallado para sugerencias específicas.
        """
        context = self._prepare_client_context(client_data, purchase_history)

        # Agregar análisis de comportamiento
        context += f"\n\nANÁLISIS DE COMPORTAMIENTO:"
        context += f"\nDías desde última compra: {days_since_last}"

        # Categorizar el comportamiento del cliente
        if days_since_last <= 30:
            behavior = "Cliente activo"
        elif days_since_last <= 90:
            behavior = "Cliente en riesgo moderado"
        elif days_since_last <= 180:
            behavior = "Cliente en riesgo alto"
        else:
            behavior = "Cliente inactivo"

        context += f"\nCategoría de comportamiento: {behavior}"

        # Análisis de productos preferidos
        if purchase_history:
            categories = {}
            total_spent = 0

            for purchase in purchase_history:
                total_spent += purchase.get('total', 0)
                for item in purchase.get('items', []):
                    category = item.get('category', 'Sin categoría')
                    categories[category] = categories.get(category, 0) + 1

            context += f"\nGasto total histórico: ${total_spent}"
            context += f"\nPromedio por compra: ${total_spent / len(purchase_history):.2f}"

            if categories:
                top_category = max(categories, key=categories.get)
                context += f"\nCategoría preferida: {top_category} ({categories[top_category]} compras)"

        return context

    def _fallback_recommendations(self, churn_score: int) -> List[Dict[str, Any]]:
        """
        Recomendaciones de respaldo cuando OpenAI no está disponible.
        """
        if churn_score >= 70:
            return [
                {
                    "type": "urgent_discount",
                    "description": "Enviar descuento del 20% inmediatamente",
                    "urgency": "alta",
                    "channel": "email",
                    "reasoning": "Cliente en riesgo crítico de abandono"
                },
                {
                    "type": "personal_call",
                    "description": "Llamada personal para entender necesidades",
                    "urgency": "alta",
                    "channel": "phone",
                    "reasoning": "Intervención directa necesaria"
                }
            ]
        elif churn_score >= 40:
            return [
                {
                    "type": "targeted_offer",
                    "description": "Oferta personalizada basada en historial",
                    "urgency": "media",
                    "channel": "email",
                    "reasoning": "Cliente en riesgo moderado"
                },
                {
                    "type": "engagement_campaign",
                    "description": "Incluir en campaña de reactivación",
                    "urgency": "media",
                    "channel": "social_media",
                    "reasoning": "Mantener engagement"
                }
            ]
        else:
            return [
                {
                    "type": "loyalty_program",
                    "description": "Invitar a programa de fidelización",
                    "urgency": "baja",
                    "channel": "email",
                    "reasoning": "Cliente estable, fomentar lealtad"
                }
            ]

    def _fallback_suggestions(self) -> List[Dict[str, Any]]:
        """
        Sugerencias de respaldo cuando OpenAI no está disponible.
        """
        return [
            {
                "type": "product_recommendation",
                "title": "Productos populares",
                "description": "Mostrar productos más vendidos de la temporada",
                "priority": "media",
                "expected_impact": "Incremento en ventas del 5-10%"
            },
            {
                "type": "seasonal_offer",
                "title": "Oferta estacional",
                "description": "Descuento en productos de temporada",
                "priority": "alta",
                "expected_impact": "Reactivación de cliente inactivo"
            }
        ]
