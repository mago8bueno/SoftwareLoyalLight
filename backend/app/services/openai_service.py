# backend/app/services/openai_service.py - VERSIÓN CORREGIDA
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Servicio OpenAI robusto con manejo de errores mejorado y fallbacks inteligentes.
    """

    def __init__(self) -> None:
        self.client = None
        self._model = "gpt-4o-mini"
        self._available = False

        # Buscar API key en orden de prioridad
        api_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("NEXT_PUBLIC_OPENAI_KEY") or 
            getattr(self._get_settings(), 'OPENAI_API_KEY', None) or
            getattr(self._get_settings(), 'NEXT_PUBLIC_OPENAI_KEY', None)
        )

        if not api_key:
            logger.warning("🔴 OpenAI API key no encontrada. Funcionalidades de IA deshabilitadas.")
            logger.info("💡 Configura OPENAI_API_KEY en tu archivo .env")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self._available = True
            logger.info("✅ OpenAI client inicializado correctamente")
        except ImportError:
            logger.error("❌ SDK de OpenAI no encontrado. Ejecuta: pip install openai>=1.0")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Error inicializando OpenAI client: {e}")
            self.client = None

    def _get_settings(self):
        """Obtiene settings de forma segura."""
        try:
            from app.core.settings import settings
            return settings
        except Exception:
            return None

    def _is_available(self) -> bool:
        """Verifica si OpenAI está disponible."""
        return self._available and self.client is not None

    def _safe_json_parse(self, text: str) -> Any:
        """Parsea JSON de forma ultra-robusta."""
        if not text or not isinstance(text, str):
            raise json.JSONDecodeError("Texto vacío o inválido", "", 0)
            
        text = text.strip()
        
        # Intento directo
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Limpiar texto común de IA (```json, etc)
        cleaned_text = re.sub(r'```json\s*', '', text)
        cleaned_text = re.sub(r'```\s*$', '', cleaned_text)
        
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass

        # Buscar arrays JSON
        array_patterns = [
            r'\[\s*\{.*?\}\s*\]',  # Array de objetos
            r'\[.*?\]',            # Cualquier array
        ]
        
        for pattern in array_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # Buscar objetos JSON
        object_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if object_match:
            try:
                return json.loads(object_match.group())
            except json.JSONDecodeError:
                pass
                
        logger.error(f"🔴 No se pudo parsear JSON de OpenAI: {text[:300]}...")
        raise json.JSONDecodeError("No se encontró JSON válido en respuesta de IA", text, 0)

    def _prepare_client_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Prepara contexto del cliente de forma robusta."""
        try:
            # Datos básicos con defaults seguros
            client_id = client_data.get("id") or client_data.get("client_id", "desconocido")
            name = client_data.get("name", "Cliente")
            email = client_data.get("email", "no-email")
            churn_score = int(client_data.get("churn_score", 0) or 0)
            segment = client_data.get("segment", "general")
            last_purchase_days = int(client_data.get("last_purchase_days", 999) or 999)
            
            # Análisis de compras robusto
            total_spent = 0
            categories = {}
            recent_items = []
            
            for purchase in (purchase_history or [])[:20]:  # Limitar a 20 más recientes
                try:
                    # Sumar total gastado
                    price = float(purchase.get("total_price", 0) or 0)
                    total_spent += price
                    
                    # Analizar items
                    items = purchase.get("items", [])
                    if not items and purchase.get("item_id"):
                        # Crear item básico si no hay items expandidos
                        items = [{
                            "id": purchase["item_id"],
                            "name": f"Producto-{purchase['item_id'][:8]}",
                            "price": price
                        }]
                    
                    for item in items:
                        item_name = str(item.get("name", "Producto"))
                        recent_items.append(item_name)
                        
                        # Categorizar producto
                        category = self._infer_category(item_name)
                        categories[category] = categories.get(category, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"Error procesando compra: {e}")
                    continue
            
            # Estadísticas calculadas
            purchase_count = len(purchase_history or [])
            avg_ticket = round(total_spent / purchase_count, 2) if purchase_count > 0 else 0
            top_category = max(categories.keys(), key=lambda k: categories[k]) if categories else "general"
            
            # Contexto estacional
            current_season = self._get_current_season()
            
            context = {
                "cliente_id": client_id,
                "nombre": name,
                "email": email,
                "segmento": segment,
                "riesgo_churn": f"{churn_score}%",
                "dias_sin_comprar": last_purchase_days,
                "temporada_actual": current_season,
                "estadisticas": {
                    "compras_realizadas": purchase_count,
                    "total_gastado": f"${total_spent:.2f}",
                    "ticket_promedio": f"${avg_ticket:.2f}",
                    "categoria_favorita": top_category,
                    "categorias": dict(list(categories.items())[:5])
                },
                "productos_recientes": recent_items[:8],
                "perfil_comportamiento": self._analyze_behavior_pattern(churn_score, last_purchase_days, purchase_count)
            }
            
            return json.dumps(context, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Error preparando contexto del cliente: {e}")
            # Contexto mínimo de emergencia
            return json.dumps({
                "nombre": client_data.get("name", "Cliente"),
                "riesgo_churn": f"{client_data.get('churn_score', 0)}%",
                "dias_sin_comprar": client_data.get("last_purchase_days", 999),
                "error": "Contexto limitado por error en procesamiento"
            })

    def _infer_category(self, item_name: str) -> str:
        """Infiere categoría de producto de forma robusta."""
        if not item_name or not isinstance(item_name, str):
            return "otros"
            
        item_lower = item_name.lower()
        
        category_patterns = {
            "camisas": ["camisa", "blusa", "camiseta", "polo", "top"],
            "pantalones": ["pantalon", "jean", "bermuda", "short", "leggin", "jogger"],
            "vestidos": ["vestido", "falda"],
            "calzado": ["zapato", "sandalia", "bota", "tenis", "sneaker", "mocasin"],
            "abrigos": ["chaqueta", "abrigo", "sueter", "cardigan", "hoodie"],
            "accesorios": ["bolso", "cartera", "mochila", "cinturon", "gorra"],
            "joyeria": ["collar", "pulsera", "anillo", "arete", "reloj"]
        }
        
        for category, keywords in category_patterns.items():
            if any(keyword in item_lower for keyword in keywords):
                return category
                
        return "otros"

    def _get_current_season(self) -> str:
        """Obtiene la temporada actual."""
        month = datetime.now().month
        if 3 <= month <= 5:
            return "primavera"
        elif 6 <= month <= 8:
            return "verano"
        elif 9 <= month <= 11:
            return "otoño"
        else:
            return "invierno"

    def _analyze_behavior_pattern(self, churn_score: int, days_since_last: int, purchase_count: int) -> str:
        """Analiza el patrón de comportamiento del cliente."""
        churn = int(churn_score or 0)
        days = int(days_since_last or 999)
        purchases = int(purchase_count or 0)
        
        if churn >= 80 or days > 120:
            return "🔴 CRÍTICO - Cliente inactivo en riesgo alto"
        elif churn >= 60 or days > 60:
            return "🟡 EN RIESGO - Cliente necesita reactivación"
        elif churn >= 40 or days > 30:
            return "🟠 ATENCIÓN - Cliente requiere seguimiento"
        elif purchases >= 5 and days <= 30:
            return "🟢 VIP - Cliente muy activo y fiel"
        else:
            return "🔵 REGULAR - Cliente con actividad normal"

    def generate_client_recommendations(
        self, 
        client_data: Dict[str, Any], 
        purchase_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones personalizadas ultra-robustas."""
        
        logger.info(f"🚀 Generando recomendaciones para cliente: {client_data.get('name', 'Unknown')}")
        
        # Fallback inmediato si OpenAI no está disponible
        if not self._is_available():
            logger.warning("⚠️  OpenAI no disponible, usando fallback inteligente")
            return self._fallback_recommendations(client_data.get("churn_score", 0))

        try:
            context = self._prepare_client_context(client_data, purchase_history)
            
            # Prompt optimizado y robusto
            prompt = f"""Eres un experto consultor en marketing de retención para tiendas de moda online con 10+ años de experiencia.

PERFIL DEL CLIENTE:
{context}

INSTRUCCIONES ESPECÍFICAS:
1. Genera exactamente 3 recomendaciones personalizadas
2. Cada recomendación debe ser específica para ESTE cliente
3. Considera su riesgo de churn, historial y temporada actual
4. Incluye timeframes y canales específicos

RESPUESTA REQUERIDA (JSON válido):
[
  {{
    "type": "discount|personal_contact|vip_offer|bundle|reactivation",
    "description": "Descripción específica mencionando categorías/productos de su historial",
    "urgency": "alta|media|baja",
    "channel": "email|whatsapp|sms|llamada",
    "reasoning": "Por qué esta recomendación es ideal para este cliente específico"
  }},
  {{
    "type": "cross_sell|loyalty_program|seasonal_offer|early_access",
    "description": "Segunda recomendación específica y personalizada",
    "urgency": "alta|media|baja", 
    "channel": "email|whatsapp|sms|llamada",
    "reasoning": "Justificación basada en el perfil del cliente"
  }},
  {{
    "type": "engagement|survey|personal_shopper|exclusive_preview",
    "description": "Tercera recomendación complementaria",
    "urgency": "alta|media|baja",
    "channel": "email|whatsapp|sms|llamada", 
    "reasoning": "Razón estratégica para esta acción"
  }}
]

IMPORTANTE: Responde ÚNICAMENTE con el array JSON válido, sin texto adicional."""

            # Llamada a OpenAI con configuración robusta
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Eres un experto en marketing de retención especializado en fashion retail. Respondes únicamente con JSON válido."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7,
                timeout=30  # Timeout de 30 segundos
            )

            content = response.choices[0].message.content
            if not content:
                raise Exception("OpenAI devolvió respuesta vacía")
                
            content = content.strip()
            logger.info(f"📝 Respuesta de OpenAI recibida: {len(content)} caracteres")
            
            # Parsear respuesta
            recommendations = self._safe_json_parse(content)
            
            # Validar estructura
            if not isinstance(recommendations, list):
                if isinstance(recommendations, dict):
                    recommendations = [recommendations]
                else:
                    raise ValueError("Respuesta no es lista ni objeto")
            
            # Limpiar y validar cada recomendación
            valid_recs = []
            for i, rec in enumerate(recommendations[:5]):  # Máximo 5 recomendaciones
                if not isinstance(rec, dict):
                    logger.warning(f"Recomendación {i} no es un objeto válido")
                    continue
                    
                # Validar campos requeridos
                required_fields = ["type", "description"]
                if not all(field in rec for field in required_fields):
                    logger.warning(f"Recomendación {i} carece de campos requeridos")
                    continue
                
                # Añadir campos faltantes con defaults
                rec.setdefault("urgency", "media")
                rec.setdefault("channel", "email")
                rec.setdefault("reasoning", "Recomendación basada en análisis de perfil del cliente")
                
                # Limpiar campos de texto
                for field in ["type", "description", "urgency", "channel", "reasoning"]:
                    if field in rec:
                        rec[field] = str(rec[field]).strip()[:500]  # Limitar longitud
                
                valid_recs.append(rec)
            
            if len(valid_recs) >= 1:
                logger.info(f"✅ OpenAI generó {len(valid_recs)} recomendaciones válidas")
                return valid_recs
            else:
                logger.warning("❌ OpenAI no generó recomendaciones válidas, usando fallback")
                return self._fallback_recommendations(client_data.get("churn_score", 0))

        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de OpenAI: {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))
        except Exception as e:
            logger.error(f"❌ Error general en OpenAI recommendations: {e}")
            return self._fallback_recommendations(client_data.get("churn_score", 0))

    def generate_client_suggestions(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
        days_since_last: int
    ) -> List[Dict[str, Any]]:
        """Genera sugerencias específicas con manejo ultra-robusto."""
        
        logger.info(f"💡 Generando sugerencias para cliente tras {days_since_last} días")
        
        if not self._is_available():
            logger.warning("⚠️  OpenAI no disponible para sugerencias, usando fallback")
            return self._fallback_suggestions()

        try:
            context = self._prepare_client_context(client_data, purchase_history)
            
            prompt = f"""Eres un consultor senior de experiencia del cliente especializado en fashion e-commerce.

CLIENTE ANALIZADO:
{context}

CONTEXTO ADICIONAL:
- Días desde última compra: {days_since_last}
- Estado: {"🔴 CRÍTICO" if days_since_last > 90 else "🟡 RIESGO" if days_since_last > 45 else "🟢 ACTIVO"}

GENERA exactamente 2-3 sugerencias específicas en formato JSON:

[
  {{
    "type": "product_bundle|experience_upgrade|personal_service|seasonal_offer",
    "title": "Título específico (máx 60 caracteres)",
    "description": "Descripción detallada con productos/categorías específicas del historial",
    "priority": "alta|media|baja",
    "expected_impact": "Impacto esperado específico y medible"
  }}
]

Responde SOLO con JSON válido, sin explicaciones adicionales."""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un experto en CX para fashion retail. Respondes solo con JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.8,
                timeout=30
            )

            content = response.choices[0].message.content
            if not content:
                raise Exception("Respuesta vacía de OpenAI")

            suggestions = self._safe_json_parse(content.strip())
            
            if not isinstance(suggestions, list):
                suggestions = [suggestions] if isinstance(suggestions, dict) else []
            
            # Validar sugerencias
            valid_suggestions = []
            for sug in suggestions[:4]:  # Máximo 4
                if isinstance(sug, dict) and all(key in sug for key in ["title", "description"]):
                    # Añadir defaults
                    sug.setdefault("priority", "media")
                    sug.setdefault("expected_impact", "Mejora en engagement del cliente")
                    
                    # Limpiar campos
                    for field in ["title", "description", "priority", "expected_impact"]:
                        if field in sug:
                            sug[field] = str(sug[field]).strip()[:400]
                    
                    valid_suggestions.append(sug)
                    
            if valid_suggestions:
                logger.info(f"✅ OpenAI generó {len(valid_suggestions)} sugerencias válidas")
                return valid_suggestions
            else:
                logger.warning("❌ Sugerencias de OpenAI no válidas, usando fallback")
                return self._fallback_suggestions()

        except Exception as e:
            logger.error(f"❌ Error generando sugerencias: {e}")
            return self._fallback_suggestions()

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Análisis de sentimiento robusto."""
        if not text or not isinstance(text, str):
            return self._fallback_sentiment()
            
        if not self._is_available():
            return self._fallback_sentiment()

        try:
            # Limitar longitud del texto
            text_clean = text.strip()[:2000]
            
            prompt = f"""Analiza el sentimiento del siguiente feedback de cliente de tienda de ropa online:

TEXTO: "{text_clean}"

Responde SOLO con este JSON:
{{
  "sentiment": "very_positive|positive|neutral|negative|very_negative",
  "confidence": 0.XX,
  "emotions": ["emotion1", "emotion2"],
  "key_phrases": ["frase1", "frase2"],
  "customer_intent": "compra|queja|consulta|devolución|elogio",
  "urgency_level": "crítico|alto|medio|bajo"
}}"""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un analista de customer sentiment para retail. Respondes solo JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.2,
                timeout=20
            )

            content = response.choices[0].message.content
            if not content:
                raise Exception("Respuesta vacía")

            result = self._safe_json_parse(content.strip())
            
            if not isinstance(result, dict):
                raise ValueError("Resultado no es objeto")

            # Validar y limpiar campos
            result.setdefault("sentiment", "neutral")
            result.setdefault("confidence", 0.5)
            result.setdefault("emotions", [])
            result.setdefault("key_phrases", [])
            result["ai_powered"] = True

            return result

        except Exception as e:
            logger.error(f"❌ Error en análisis de sentimiento: {e}")
            return self._fallback_sentiment()

    def _fallback_recommendations(self, churn_score: int) -> List[Dict[str, Any]]:
        """Fallback inteligente para recomendaciones."""
        churn = int(churn_score or 0)
        season = self._get_current_season()
        
        if churn >= 80:
            return [
                {
                    "type": "urgent_reactivation",
                    "description": f"Oferta flash 30% OFF en colección {season} válida 48h + envío gratis",
                    "urgency": "alta",
                    "channel": "whatsapp",
                    "reasoning": "Cliente en riesgo crítico requiere intervención urgente con alto valor"
                },
                {
                    "type": "personal_contact",
                    "description": "Llamada personal de 10 min para entender sus necesidades actuales",
                    "urgency": "alta", 
                    "channel": "llamada",
                    "reasoning": "Contacto humano directo para reconectar emocionalmente"
                }
            ]
        elif churn >= 50:
            return [
                {
                    "type": "targeted_offer",
                    "description": f"Descuento 20% personalizado en su categoría favorita + preview {season}",
                    "urgency": "media",
                    "channel": "email",
                    "reasoning": "Cliente en riesgo medio necesita incentivo relevante personalizado"
                },
                {
                    "type": "loyalty_program",
                    "description": "Puntos de fidelidad dobles en próximas 2 compras + gift sorpresa",
                    "urgency": "media",
                    "channel": "email",
                    "reasoning": "Reforzar conexión con programa de lealtad y generar exclusividad"
                }
            ]
        else:
            return [
                {
                    "type": "cross_sell",
                    "description": f"Bundle recomendado: combina productos de sus categorías favoritas con 15% extra",
                    "urgency": "baja",
                    "channel": "email", 
                    "reasoning": "Cliente estable, oportunidad de aumentar ticket promedio con productos complementarios"
                }
            ]

    def _fallback_suggestions(self) -> List[Dict[str, Any]]:
        """Fallback inteligente para sugerencias."""
        return [
            {
                "type": "product_bundle",
                "title": "Pack personalizado basado en historial",
                "description": "Crear bundle con 2-3 productos de categorías más compradas con descuento del 15%",
                "priority": "alta",
                "expected_impact": "Incremento del 20% en ticket promedio"
            },
            {
                "type": "engagement_action",
                "title": "Quiz de estilo personal en 60 segundos",
                "description": "Encuesta interactiva para conocer preferencias de colores, estilos y ocasiones de uso",
                "priority": "media",
                "expected_impact": "Mejora del 30% en precisión de recomendaciones futuras"
            }
        ]

    def _fallback_sentiment(self) -> Dict[str, Any]:
        """Fallback para análisis de sentimiento."""
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotions": [],
            "key_phrases": [],
            "customer_intent": "consulta",
            "urgency_level": "medio",
            "ai_powered": False
        }

    def get_status(self) -> Dict[str, Any]:
        """Estado del servicio OpenAI."""
        return {
            "available": self._is_available(),
            "model": self._model,
            "features": ["recommendations", "suggestions", "sentiment_analysis"],
            "fallback_enabled": True,
            "last_check": datetime.now().isoformat()
        }
