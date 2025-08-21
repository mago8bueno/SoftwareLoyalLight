# backend/app/services/openai_service.py
from __future__ import annotations

import json
import logging
import os
import re
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import PyPDF2
import docx
from io import BytesIO

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    Sistema de conocimiento empresarial para contextualizar las recomendaciones de IA.
    Permite cargar PDFs, documentos y crear una base de conocimiento específica del negocio.
    """
    
    def __init__(self):
        self.knowledge_data = {}
        self.load_default_knowledge()
    
    def load_default_knowledge(self):
        """Carga conocimiento base del negocio de ropa/fashion."""
        self.knowledge_data = {
            "seasonal_trends": {
                "primavera": ["colores pastel", "tejidos ligeros", "chaquetas", "vestidos florales"],
                "verano": ["colores vibrantes", "shorts", "camisetas", "sandalias", "sombreros"],
                "otoño": ["colores tierra", "suéteres", "botas", "chaquetas de cuero"],
                "invierno": ["colores oscuros", "abrigos", "bufandas", "botas térmicas"]
            },
            "cross_sell_rules": {
                "camisas": ["pantalones", "chaquetas", "accesorios"],
                "pantalones": ["camisas", "cinturones", "zapatos"],
                "vestidos": ["zapatos", "bolsos", "joyería"],
                "zapatos": ["medias", "cuidado de calzado", "plantillas"]
            },
            "customer_segments": {
                "joven_trendy": {
                    "age_range": "18-25",
                    "interests": ["tendencias", "redes sociales", "fast fashion"],
                    "channels": ["instagram", "tiktok", "email"],
                    "price_sensitivity": "alta"
                },
                "profesional": {
                    "age_range": "26-40", 
                    "interests": ["calidad", "versatilidad", "trabajo"],
                    "channels": ["email", "linkedin", "whatsapp"],
                    "price_sensitivity": "media"
                },
                "maduro_premium": {
                    "age_range": "40+",
                    "interests": ["calidad premium", "durabilidad", "comodidad"],
                    "channels": ["email", "llamada", "presencial"],
                    "price_sensitivity": "baja"
                }
            },
            "churn_patterns": {
                "alta_frecuencia": "Cliente que compra semanalmente y deja de hacerlo",
                "estacional": "Cliente que compra en temporadas específicas",
                "ocasional": "Cliente que compra para eventos especiales",
                "price_sensitive": "Cliente que solo compra con descuentos"
            },
            "retention_strategies": {
                "descuento_progresivo": "Aumentar descuento según días sin comprar",
                "bundle_personalizado": "Agrupar productos basado en historial",
                "early_access": "Acceso anticipado a nuevas colecciones",
                "loyalty_points": "Puntos extra en categorías favoritas"
            }
        }
    
    def add_pdf_knowledge(self, pdf_content: bytes, category: str = "general") -> str:
        """Extrae texto de PDF y lo añade a la base de conocimiento."""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"
            
            # Crear hash único para el documento
            doc_hash = hashlib.md5(pdf_content).hexdigest()[:8]
            
            # Almacenar en knowledge base
            if category not in self.knowledge_data:
                self.knowledge_data[category] = {}
            
            self.knowledge_data[category][f"document_{doc_hash}"] = {
                "content": text_content,
                "type": "pdf",
                "added_at": datetime.now().isoformat(),
                "summary": self._extract_key_points(text_content)
            }
            
            logger.info(f"PDF añadido a knowledge base: categoría '{category}', hash {doc_hash}")
            return doc_hash
            
        except Exception as e:
            logger.error(f"Error procesando PDF: {e}")
            raise
    
    def add_text_knowledge(self, content: str, title: str, category: str = "general") -> str:
        """Añade conocimiento en formato texto."""
        doc_id = f"text_{hashlib.md5(content.encode()).hexdigest()[:8]}"
        
        if category not in self.knowledge_data:
            self.knowledge_data[category] = {}
            
        self.knowledge_data[category][doc_id] = {
            "title": title,
            "content": content,
            "type": "text",
            "added_at": datetime.now().isoformat(),
            "summary": self._extract_key_points(content)
        }
        
        return doc_id
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extrae puntos clave de un texto (versión básica)."""
        # Buscar patrones comunes de información importante
        lines = text.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:  # Longitud razonable
                # Buscar líneas que parezcan importantes
                if any(word in line.lower() for word in [
                    'importante', 'clave', 'estrategia', 'objetivo', 
                    'resultado', 'tendencia', 'recomendación'
                ]):
                    key_points.append(line)
                # Buscar líneas con números/porcentajes
                elif re.search(r'\d+%|\d+\.\d+', line):
                    key_points.append(line)
                    
        return key_points[:10]  # Máximo 10 puntos clave
    
    def get_context_for_client(self, client_data: Dict, category: str = None) -> str:
        """Obtiene contexto relevante de la knowledge base para un cliente."""
        relevant_context = []
        
        # Contexto estacional
        current_month = datetime.now().month
        if 3 <= current_month <= 5:  # Primavera
            season = "primavera"
        elif 6 <= current_month <= 8:  # Verano
            season = "verano"
        elif 9 <= current_month <= 11:  # Otoño
            season = "otoño"
        else:  # Invierno
            season = "invierno"
            
        seasonal_trends = self.knowledge_data.get("seasonal_trends", {}).get(season, [])
        if seasonal_trends:
            relevant_context.append(f"Tendencias actuales ({season}): {', '.join(seasonal_trends)}")
        
        # Contexto de segmento
        segment = client_data.get("segment", "general")
        if segment in self.knowledge_data.get("customer_segments", {}):
            segment_info = self.knowledge_data["customer_segments"][segment]
            relevant_context.append(f"Perfil del segmento '{segment}': {json.dumps(segment_info)}")
        
        # Cross-sell basado en categoría favorita
        fav_category = client_data.get("last_category", "").lower()
        cross_sell = self.knowledge_data.get("cross_sell_rules", {}).get(fav_category, [])
        if cross_sell:
            relevant_context.append(f"Productos complementarios a {fav_category}: {', '.join(cross_sell)}")
        
        # Documentos específicos de la categoría si se proporciona
        if category and category in self.knowledge_data:
            for doc_id, doc_data in self.knowledge_data[category].items():
                if doc_data.get("summary"):
                    relevant_context.append(f"Conocimiento empresarial: {', '.join(doc_data['summary'][:3])}")
        
        return "\n".join(relevant_context)


class OpenAIService:
    """
    Servicio avanzado para generar recomendaciones con IA contextualizada.
    Integra knowledge base empresarial y prompts optimizados.
    """

    def __init__(self) -> None:
        self.client = None
        self.knowledge_base = KnowledgeBase()

        # Buscar API key
        api_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("NEXT_PUBLIC_OPENAI_KEY")
        )

        if not api_key:
            logger.warning("OpenAI API key no encontrada. Funcionalidades de IA deshabilitadas.")
            return

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self._model = "gpt-4o-mini"
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
        """Parsea JSON de forma segura."""
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar bloques JSON
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass
        
        object_match = re.search(r'\{.*\}', text, re.DOTALL)
        if object_match:
            try:
                return json.loads(object_match.group())
            except json.JSONDecodeError:
                pass
                
        logger.error(f"No se pudo parsear JSON de: {text[:200]}...")
        raise json.JSONDecodeError("No se encontró JSON válido", text, 0)

    def _prepare_enhanced_client_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Prepara contexto enriquecido del cliente con knowledge base."""
        
        # Datos básicos del cliente
        basic_context = self._prepare_basic_context(client_data, purchase_history)
        
        # Contexto empresarial de la knowledge base
        business_context = self.knowledge_base.get_context_for_client(client_data)
        
        # Análisis de comportamiento avanzado
        behavior_analysis = self._analyze_customer_behavior(client_data, purchase_history)
        
        return f"""PERFIL DEL CLIENTE:
{basic_context}

CONTEXTO EMPRESARIAL:
{business_context}

ANÁLISIS DE COMPORTAMIENTO:
{behavior_analysis}"""

    def _prepare_basic_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Contexto básico del cliente."""
        name = client_data.get("name", "Cliente")
        churn_score = client_data.get("churn_score", 0)
        segment = client_data.get("segment", "general")
        last_purchase_days = client_data.get("last_purchase_days", 999)
        
        # Análisis de compras
        total_spent = sum(p.get("total_price", 0) for p in purchase_history)
        avg_ticket = total_spent / len(purchase_history) if purchase_history else 0
        
        # Categorías más compradas
        categories = {}
        for purchase in purchase_history:
            items = purchase.get("items", [])
            for item in items:
                category = self._infer_category(item.get("name", ""))
                categories[category] = categories.get(category, 0) + 1
        
        top_category = max(categories.keys(), key=lambda k: categories[k]) if categories else "general"
        
        return f"""- Nombre: {name}
- Segmento: {segment}
- Riesgo de churn: {churn_score}%
- Días sin comprar: {last_purchase_days}
- Total gastado: ${total_spent:.2f}
- Ticket promedio: ${avg_ticket:.2f}
- Compras realizadas: {len(purchase_history)}
- Categoría favorita: {top_category}
- Distribución de categorías: {dict(list(categories.items())[:3])}"""

    def _analyze_customer_behavior(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Análisis avanzado del comportamiento del cliente."""
        if not purchase_history:
            return "- Cliente nuevo sin historial de compras"
        
        # Frecuencia de compra
        if len(purchase_history) >= 5:
            frequency = "alta"
        elif len(purchase_history) >= 2:
            frequency = "media"
        else:
            frequency = "baja"
        
        # Estacionalidad (básica)
        months = []
        for purchase in purchase_history:
            if purchase.get("purchased_at"):
                try:
                    month = datetime.fromisoformat(purchase["purchased_at"]).month
                    months.append(month)
                except:
                    pass
        
        seasonal_pattern = "No identificado"
        if months:
            most_common_month = max(set(months), key=months.count)
            if 6 <= most_common_month <= 8:
                seasonal_pattern = "Comprador de verano"
            elif 11 <= most_common_month <= 12 or most_common_month <= 2:
                seasonal_pattern = "Comprador de invierno/fiestas"
        
        # Sensibilidad al precio
        prices = [p.get("total_price", 0) for p in purchase_history]
        avg_price = sum(prices) / len(prices) if prices else 0
        if avg_price > 100:
            price_sensitivity = "baja"
        elif avg_price > 50:
            price_sensitivity = "media"
        else:
            price_sensitivity = "alta"
        
        return f"""- Frecuencia de compra: {frequency}
- Patrón estacional: {seasonal_pattern}
- Sensibilidad al precio: {price_sensitivity}
- Ticket promedio: ${avg_price:.2f}
- Última compra: hace {client_data.get("last_purchase_days", 999)} días"""

    def _infer_category(self, item_name: str) -> str:
        """Infiere la categoría de un producto basado en su nombre."""
        item_lower = item_name.lower()
        
        if any(word in item_lower for word in ['camisa', 'blusa', 'camiseta', 'polo', 'top']):
            return 'camisas_tops'
        elif any(word in item_lower for word in ['pantalon', 'jean', 'bermuda', 'short', 'leggin']):
            return 'pantalones'
        elif any(word in item_lower for word in ['vestido', 'falda']):
            return 'vestidos_faldas'
        elif any(word in item_lower for word in ['zapato', 'sandalia', 'bota', 'tenis', 'sneaker']):
            return 'calzado'
        elif any(word in item_lower for word in ['chaqueta', 'abrigo', 'sueter', 'cardigan']):
            return 'abrigo'
        elif any(word in item_lower for word in ['bolso', 'cartera', 'mochila']):
            return 'bolsos'
        elif any(word in item_lower for word in ['collar', 'pulsera', 'anillo', 'arete']):
            return 'accesorios'
        else:
            return 'otros'

    def generate_client_recommendations(
        self, 
        client_data: Dict[str, Any], 
        purchase_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones personalizadas con IA contextualizada."""
        
        if not self._is_available():
            return self._fallback_recommendations(client_data.get("churn_score", 0))

        try:
            context = self._prepare_enhanced_client_context(client_data, purchase_history)
            
            # Prompt optimizado con contexto empresarial
            prompt = f"""Eres María, una experta consultora en marketing de retención con 15 años de experiencia en retail de moda. Has ayudado a cientos de marcas a reducir el churn y aumentar el CLV.

SITUACIÓN:
{context}

TU MISIÓN:
Genera 3-4 recomendaciones ultra-específicas y accionables para este cliente. Cada recomendación debe ser tan personalizada que el cliente sienta que fue diseñada exclusivamente para él.

CRITERIOS DE EXCELENCIA:
1. ESPECÍFICO: Menciona productos, categorías, colores o estilos concretos
2. URGENTE: Define timeframes claros (24h, 7 días, etc.)
3. PERSONAL: Referencias directas a su historial de compra
4. MEDIBLE: Incluye métricas esperadas cuando sea relevante

FORMATO DE RESPUESTA (JSON):
[
  {{
    "type": "discount_targeted|vip_treatment|bundle_offer|early_access|personal_shopper",
    "title": "Título que capture atención (máx 60 caracteres)",
    "description": "Descripción específica mencionando productos/categorías de su historial",
    "urgency": "crítica|alta|media",
    "channel": "email_personalizado|whatsapp_vip|llamada_personal|sms_exclusivo",
    "timing": "inmediato|dentro_24h|esta_semana|próximos_7dias",
    "expected_conversion": "15-25%|10-15%|5-10%",
    "reasoning": "Por qué esta recomendación es perfecta para ESTE cliente específico"
  }}
]

EJEMPLOS DE EXCELENCIA:
✅ "Descuento VIP del 30% en camisas blancas y azules (tus favoritas) + jean clásico - válido 48h"
✅ "Acceso exclusivo pre-lanzamiento: nueva colección otoño en tu talla M, categorías que más compras"
❌ "Enviar newsletter con ofertas generales" (muy genérico)
❌ "Mostrar productos populares" (no personalizado)

Responde SOLO con el JSON, sin explicaciones adicionales."""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres María, consultora experta en retención de clientes con 15 años de experiencia en retail de moda."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.7
            )

            content = response.choices[0].message.content.strip()
            recommendations = self._safe_json_parse(content)
            
            if not isinstance(recommendations, list):
                recommendations = [recommendations] if isinstance(recommendations, dict) else []
            
            # Validar y limpiar recomendaciones
            valid_recs = []
            for rec in recommendations:
                if isinstance(rec, dict) and all(key in rec for key in ["type", "description"]):
                    # Añadir campos faltantes con defaults
                    rec.setdefault("urgency", "media")
                    rec.setdefault("channel", "email")
                    rec.setdefault("reasoning", "Recomendación basada en análisis de perfil")
                    valid_recs.append(rec)
                    
            if valid_recs:
                logger.info(f"OpenAI generó {len(valid_recs)} recomendaciones de alta calidad")
                return valid_recs
            else:
                logger.warning("Recomendaciones de OpenAI no válidas, usando fallback inteligente")
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
        """Genera sugerencias específicas con IA contextualizada."""
        
        if not self._is_available():
            return self._fallback_suggestions()

        try:
            context = self._prepare_enhanced_client_context(client_data, purchase_history)
            
            prompt = f"""Eres Carlos, un consultor senior de experiencia del cliente especializado en fashion retail con un track record de aumentar el AOV en 40% y la satisfacción del cliente en 35%.

CLIENTE ANALIZADO:
{context}

CONTEXTO ADICIONAL:
- Días desde última compra: {days_since_last}
- Estado del cliente: {"🔴 CRÍTICO" if days_since_last > 90 else "🟡 EN RIESGO" if days_since_last > 45 else "🟢 ACTIVO"}

TU OBJETIVO:
Crear 2-3 sugerencias innovadoras que no solo generen una venta, sino que mejoren la experiencia y fidelicen al cliente a largo plazo.

ENFOQUE ESTRATÉGICO:
- Si es cliente crítico (>90 días): Enfoque en REACTIVACIÓN con alto valor percibido
- Si está en riesgo (45-90 días): Enfoque en RETENCIÓN con relevancia personal  
- Si está activo (<45 días): Enfoque en CRECIMIENTO con upsell/cross-sell

FORMATO JSON:
[
  {{
    "type": "product_bundle|experience_upgrade|vip_program|personal_styling|seasonal_collection",
    "title": "Título atractivo (máx 50 caracteres)",
    "description": "Descripción detallada con productos/categorías específicas basadas en su historial",
    "value_proposition": "¿Por qué es irresistible para ESTE cliente?",
    "implementation": "¿Cómo ejecutar esta sugerencia?",
    "priority": "crítica|alta|media",
    "expected_revenue_increase": "+15-30%|+10-20%|+5-15%",
    "timeline": "inmediato|1_semana|1_mes"
  }}
]

EJEMPLOS GANADORES:
✅ "Bundle 'Tu Look Perfecto': camisa + pantalón + zapatos de tus marcas favoritas con descuento especial"
✅ "Servicio Personal Shopper virtual: sesión de 30 min para encontrar tu próximo look profesional"
✅ "Acceso VIP: pre-orden de la nueva colección en tu talla M antes del lanzamiento público"

Responde SOLO con JSON válido."""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres Carlos, consultor senior de experiencia del cliente con expertise en fashion retail."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=900,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            suggestions = self._safe_json_parse(content)
            
            if not isinstance(suggestions, list):
                suggestions = [suggestions] if isinstance(suggestions, dict) else []
            
            valid_suggestions = []
            for sug in suggestions:
                if isinstance(sug, dict) and all(key in sug for key in ["title", "description"]):
                    # Añadir campos faltantes
                    sug.setdefault("priority", "media")
                    sug.setdefault("expected_impact", "Mejora en engagement del cliente")
                    valid_suggestions.append(sug)
                    
            if valid_suggestions:
                logger.info(f"OpenAI generó {len(valid_suggestions)} sugerencias de alta calidad")
                return valid_suggestions
            else:
                return self._fallback_suggestions()

        except Exception as e:
            logger.error(f"Error generando sugerencias con OpenAI: {e}")
            return self._fallback_suggestions()

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Análisis avanzado de sentimiento con contexto empresarial."""
        if not self._is_available():
            return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "key_phrases": [], "ai_powered": False}

        try:
            prompt = f"""Eres un analista experto en customer feedback para retail de moda. 

TEXTO A ANALIZAR:
"{text}"

Analiza el sentimiento considerando el contexto de una tienda de ropa online y devuelve SOLO JSON:

{{
  "sentiment": "very_positive|positive|neutral|negative|very_negative",
  "confidence": 0.XX,
  "emotions": ["joy","trust","excitement","disappointment","frustration","anger"],
  "key_phrases": ["frases importantes extraídas"],
  "customer_intent": "compra|queja|consulta|devolución|elogio|sugerencia",
  "urgency_level": "crítico|alto|medio|bajo",
  "recommended_action": "respuesta_inmediata|seguimiento_24h|respuesta_estándar|archivar",
  "business_impact": "alto_valor|oportunidad_mejora|cliente_satisfecho|riesgo_churn"
}}"""

            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un analista experto en customer sentiment para retail."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.2
            )

            content = response.choices[0].message.content.strip()
            result = self._safe_json_parse(content)

            if not isinstance(result, dict):
                raise ValueError("Respuesta de sentiment no válida")

            # Asegurar campos mínimos
            result.setdefault("sentiment", "neutral")
            result.setdefault("confidence", 0.5)
            result.setdefault("emotions", [])
            result.setdefault("key_phrases", [])
            result["ai_powered"] = True

            return result

        except Exception as e:
            logger.error(f"Error analizando sentimiento: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "emotions": [], "key_phrases": [], "ai_powered": False}

    # Métodos para añadir conocimiento empresarial
    def add_business_knowledge(self, content: str, title: str, category: str = "general") -> str:
        """Añade conocimiento empresarial al sistema."""
        return self.knowledge_base.add_text_knowledge(content, title, category)
    
    def add_pdf_knowledge(self, pdf_content: bytes, category: str = "general") -> str:
        """Añade conocimiento desde PDF."""
        return self.knowledge_base.add_pdf_knowledge(pdf_content, category)
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del conocimiento disponible."""
        summary = {}
        for category, docs in self.knowledge_base.knowledge_data.items():
            if isinstance(docs, dict):
                summary[category] = {
                    "documents": len(docs),
                    "titles": [doc.get("title", doc_id) for doc_id, doc in docs.items() if isinstance(doc, dict)]
                }
            else:
                summary[category] = "Built-in knowledge"
        return summary

    def _fallback_recommendations(self, churn_score: int) -> List[Dict[str, Any]]:
        """Fallback inteligente basado en churn score."""
        churn = int(churn_score or 0)
        current_season = self._get_current_season()
        
        if churn >= 80:
            return [
                {
                    "type": "urgent_reactivation",
                    "title": "¡Te extrañamos! Oferta exclusiva 48h",
                    "description": f"30% OFF en toda la colección {current_season} + envío gratis. Válido solo 48 horas.",
                    "urgency": "crítica",
                    "channel": "whatsapp_personal",
                    "timing": "inmediato",
                    "reasoning": "Cliente en riesgo crítico necesita intervención urgente con alto valor percibido"
                },
                {
                    "type": "vip_treatment", 
                    "title": "Asesoría personal gratuita",
                    "description": "Llamada de 15 min con nuestra estilista para encontrar tu look perfecto.",
                    "urgency": "alta",
                    "channel": "llamada_personal",
                    "timing": "dentro_24h",
                    "reasoning": "Contacto humano directo para recuperar conexión emocional"
                }
            ]
        elif churn >= 50:
            return [
                {
                    "type": "targeted_offer",
                    "title": f"Especial {current_season} para ti",
                    "description": f"20% OFF en tu categoría favorita + preview exclusivo nuev
        ]
