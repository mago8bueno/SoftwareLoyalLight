# backend/app/services/openai_service.py
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Servicio para generar recomendaciones, sugerencias y análisis de sentimiento
    usando OpenAI GPT. Incluye manejo robusto de errores y fallbacks.
    """

    def __init__(self) -> None:
        self.client = None

        # 1) Buscar API key en orden de prioridad
        api_key = (
            os.getenv("OPENAI_API_KEY") or          # Estándar para backend
            os.getenv("NEXT_PUBLIC_OPENAI_KEY")     # Fallback (no recomendado)
        )

        if not api_key:
            logger.warning("OpenAI API key no encontrada. Funcionalidades de IA deshabilitadas.")
            return

        try:
            # Usar SDK moderno de OpenAI (v1.0+)
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self._model = "gpt-4o-mini"  # Modelo eficiente
            logger.info("OpenAI client inicializado correctamente")
        except ImportError:
            logger.error("SDK de OpenAI no encontrado. Instala: pip install openai>=1.0")
            self.client = None
        except Exception as e:
            logger.error(f"Error inicializando OpenAI client: {e}")
            self.client = None

    def _is_available(self) -> bool:
        """Verifica si OpenAI está disponible."""
        return self.client is not None

    def _safe_json_parse(self, text: str) -> Any:
        """Parsea JSON de forma segura, extrayendo bloques JSON válidos."""
        text = text.strip()
        
        # Intento directo
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar bloques JSON en el texto
        import re
        
        # Buscar arrays JSON
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass
        
        # Buscar objetos JSON
        object_match = re.search(r'\{.*\}', text, re.DOTALL)
        if object_match:
            try:
                return json.loads(object_match.group())
            except json.JSONDecodeError:
                pass
                
        logger.error(f"No se pudo parsear JSON de: {text[:200]}...")
        raise json.JSONDecodeError("No se encontró JSON válido", text, 0)

    def _prepare_client_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Prepara contexto del cliente para OpenAI."""
        
        # Datos básicos
        name = client_data.get("name", "N/A")
        email = client_data.get("email", "N/A")
        churn_score = client_data.get("churn_score", 0)
        segment = client_data.get("segment", "general")
        last_purchase_days = client_data.get("last_purchase_days", 999)
        total_spent = client_data.get("total_spent", 0)
        
        # Análisis del historial
        categories = {}
        recent_items = []
        
        for purchase in (purchase_history or [])[:10]:  # Últimas 10 compras
            # Analizar items si están disponibles
            items = purchase.get("items", [])
            if not items and "item_id" in purchase:
                # Si no hay items expandidos, crear uno básico
                items = [{"id": purchase["item_id"], "name": "Producto", "price": purchase.get("total_price", 0)}]
            
            for item in items:
                item_name = item.get("name", "Producto sin nombre")
                recent_items.append(item_name)
                
                # Inferir categoría del nombre (básico)
                item_lower = item_name.lower()
                if any(word in item_lower for word in ['camisa', 'blusa', 'camiseta']):
                    category = 'camisas'
                elif any(word in item_lower for word in ['pantalon', 'jean', 'bermuda']):
                    category = 'pantalones'
                elif any(word in item_lower for word in ['zapato', 'sandalia', 'bota']):
                    category = 'calzado'
                else:
                    category = 'otros'
                
                categories[category] = categories.get(category, 0) + 1

        top_category = max(categories.keys(), key=lambda k: categories[k]) if categories else "general"
        
        context = {
            "nombre": name,
            "email": email,
            "segmento": segment,
            "riesgo_churn": f"{churn_score}%",
            "dias_sin_comprar": last_purchase_days,
            "total_gastado": f"${total_spent}",
            "compras_realizadas": len(purchase_history or []),
            "categoria_preferida": top_category,
            "productos_recientes": recent_items[:5],
        }
        
        return json.dumps(context, ensure_ascii=False, indent=2)

    def generate_client_recommendations(
        self, 
        client_data: Dict[str, Any], 
        purchase_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones personalizadas usando OpenAI."""
        
        if not self._is_available():
            logger.info("OpenAI no disponible, usando fallback para recomendaciones")
            return self._fallback_recommendations(client_data.get("churn_score", 0))

        try:
            context = self._prepare_client_context(client_data, purchase_history)
            
            prompt = f"""Eres un experto en marketing de retención para una tienda de ropa online.

PERFIL DEL CLIENTE:
{context}

INSTRUCCIONES:
1. Genera 3-4 recomendaciones específicas y personalizadas para este cliente
2. Considera su riesgo de churn, categorías preferidas y comportamiento de compra
3. Cada recomendación debe ser accionable y específica

RESPONDE SOLO CON UN JSON ARRAY:
[
  {{
    "type": "discount|personal_message|call|email_sequence|loyalty_offer",
    "description": "Descripción específica de la acción (menciona categorías o productos concretos)",
    "urgency": "alta|media|baja",
    "channel": "email|sms|whatsapp|llamada|app",
    "reasoning": "Por qué esta recomendación funciona para este cliente específico"
  }}
]

Ejemplo de buena recomendación:
"Enviar cupón del 20% en camisas (su categoría favorita) válido por 7 días, ya que no compra hace 45 días"

NO uses recomendaciones genéricas como "mostrar productos populares"."""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un experto en marketing de retención y personalización."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            content = response.choices[0].message.content.strip()
            recommendations = self._safe_json_parse(content)
            
            # Validar que sea una lista
            if not isinstance(recommendations, list):
                recommendations = [recommendations] if isinstance(recommendations, dict) else []
            
            # Validar estructura de cada recomendación
            valid_recs = []
            for rec in recommendations:
                if isinstance(rec, dict) and all(key in rec for key in ["type", "description", "urgency"]):
                    valid_recs.append(rec)
                    
            if valid_recs:
                logger.info(f"OpenAI generó {len(valid_recs)} recomendaciones válidas")
                return valid_recs
            else:
                logger.warning("Recomendaciones de OpenAI no válidas, usando fallback")
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
        """Genera sugerencias específicas usando OpenAI."""
        
        if not self._is_available():
            logger.info("OpenAI no disponible, usando fallback para sugerencias")
            return self._fallback_suggestions()

        try:
            context = self._prepare_client_context(client_data, purchase_history)
            
            prompt = f"""Eres un consultor de experiencia del cliente para una tienda de ropa online.

PERFIL DEL CLIENTE:
{context}

ANÁLISIS ADICIONAL:
- Días desde última compra: {days_since_last}
- Comportamiento: {"Muy activo" if days_since_last < 15 else "Activo" if days_since_last < 45 else "En riesgo" if days_since_last < 90 else "Inactivo"}

GENERA 2-3 sugerencias específicas para:
- Productos concretos basados en su historial
- Ofertas personalizadas (packs, cross-sell)
- Acciones de engagement específicas

RESPONDE SOLO CON JSON:
[
  {{
    "type": "product_recommendation|bundle_offer|cross_sell|engagement_action",
    "title": "Título específico (menciona productos o categorías concretas)",
    "description": "Descripción detallada con productos/categorías específicas",
    "priority": "alta|media|baja",
    "expected_impact": "Impacto esperado específico (ej: 'Incremento 15% en ticket promedio')"
  }}
]

EJEMPLO de buena sugerencia:
"Pack de camisas + pantalón con 15% extra (combina sus 2 categorías favoritas)"

NO uses sugerencias genéricas como "productos populares" o "ofertas estacionales"."""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un experto en personalización de experiencias de compra."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            suggestions = self._safe_json_parse(content)
            
            if not isinstance(suggestions, list):
                suggestions = [suggestions] if isinstance(suggestions, dict) else []
            
            # Validar estructura
            valid_suggestions = []
            for sug in suggestions:
                if isinstance(sug, dict) and all(key in sug for key in ["title", "description"]):
                    valid_suggestions.append(sug)
                    
            if valid_suggestions:
                logger.info(f"OpenAI generó {len(valid_suggestions)} sugerencias válidas")
                return valid_suggestions
            else:
                logger.warning("Sugerencias de OpenAI no válidas, usando fallback")
                return self._fallback_suggestions()

        except Exception as e:
            logger.error(f"Error generando sugerencias con OpenAI: {e}")
            return self._fallback_suggestions()

    def _fallback_recommendations(self, churn_score: int) -> List[Dict[str, Any]]:
        """Fallback inteligente basado en churn score."""
        churn = int(churn_score or 0)
        
        if churn >= 80:
            return [
                {
                    "type": "urgent_discount",
                    "description": "Descuento urgente del 25% válido por 48 horas para reactivar compras",
                    "urgency": "alta",
                    "channel": "email",
                    "reasoning": "Cliente en riesgo crítico requiere intervención inmediata"
                },
                {
                    "type": "personal_call", 
                    "description": "Llamada personal para entender qué productos necesita",
                    "urgency": "alta",
                    "channel": "llamada",
                    "reasoning": "Contacto directo para recuperar cliente de alto valor"
                }
            ]
        elif churn >= 50:
            return [
                {
                    "type": "targeted_offer",
                    "description": "Oferta personalizada en su categoría de compra más frecuente",
                    "urgency": "media", 
                    "channel": "email",
                    "reasoning": "Cliente en riesgo moderado necesita incentivo relevante"
                },
                {
                    "type": "loyalty_offer",
                    "description": "Puntos de fidelidad dobles en su próxima compra",
                    "urgency": "media",
                    "channel": "app",
                    "reasoning": "Reforzar vínculo con programa de lealtad"
                }
            ]
        else:
            return [
                {
                    "type": "upsell",
                    "description": "Recomendación de productos complementarios a sus compras anteriores", 
                    "urgency": "baja",
                    "channel": "email",
                    "reasoning": "Cliente estable, oportunidad de aumentar ticket promedio"
                }
            ]

    def _fallback_suggestions(self) -> List[Dict[str, Any]]:
        """Fallback inteligente para sugerencias."""
        return [
            {
                "type": "cross_sell",
                "title": "Pack personalizado basado en historial",
                "description": "Combinar 2-3 productos de categorías que el cliente ya compra con descuento del 10%",
                "priority": "alta",
                "expected_impact": "Incremento del 15-20% en ticket promedio"
            },
            {
                "type": "engagement_action",
                "title": "Encuesta de preferencias de 30 segundos",
                "description": "Quiz breve para conocer colores, tallas y estilos preferidos del cliente",
                "priority": "media", 
                "expected_impact": "Mejora en precisión de recomendaciones futuras"
            }
        ]
