# backend/app/services/openai_service.py
from __future__ import annotations

import json
import logging
import os
import re
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from io import BytesIO

# Dependencias opcionales: no rompen la app si no están instaladas
try:
    import PyPDF2  # type: ignore
except Exception:
    PyPDF2 = None  # noqa: N816

logger = logging.getLogger(__name__)


# -------- Utilidades de localización/temporadas (LatAm) -------- #

_LATAM_SOUTH_HEMISPHERE = {
    # Con estaciones invertidas respecto a Europa/USA
    "argentina", "chile", "uruguay", "paraguay", "bolivia",
    # Brasil es mixto; asumimos sur por defecto para retail urbano
    "brasil", "brazil",
    # Perú es mixto; asumimos costa/andina sur como inversión
    "peru", "perú",
}

_LATAM_TROPICAL = {
    # Tropical (lluvias/seca). México: gran parte tropical para retail masivo
    "mexico", "méxico", "colombia", "venezuela", "ecuador",
    "panama", "panamá", "costa rica", "costa-rica", "nicaragua",
    "honduras", "el salvador", "el salvador", "guatemala",
    "republica dominicana", "república dominicana", "dominican republic",
    "puerto rico", "cuba", "haiti", "haití",
    # Norte/Noreste de Brasil (gran base tropical)
    "manaus", "belem", "belém",
}

def _normalize_country(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip().lower()


def get_latam_season(today: Optional[datetime] = None, country_or_city: Optional[str] = None) -> str:
    """
    Devuelve la 'temporada' comercial para LATAM:
    - Hemisferio sur: estaciones invertidas (primavera/verano/otoño/invierno).
    - Tropical: 'lluvias' (aprox. mayo-octubre) o 'seca' (nov-abril).
    - Si no se conoce país/ciudad: asumimos tropical (retail online panregional).
    """
    dt = today or datetime.now()
    country = _normalize_country(country_or_city)

    # Heurística simple por pertenencia a conjuntos
    if country in _LATAM_SOUTH_HEMISPHERE:
        # Invertidas vs. España
        m = dt.month
        if 9 <= m <= 11:
            return "primavera"   # (Sep-Nov)
        elif 12 <= m or m <= 2:
            return "verano"      # (Dic-Feb)
        elif 3 <= m <= 5:
            return "otoño"       # (Mar-May)
        else:
            return "invierno"    # (Jun-Ago)

    # Tropical por defecto si no está explícito en sur
    m = dt.month
    if 5 <= m <= 10:
        return "lluvias"
    else:
        return "seca"


class KnowledgeBase:
    """
    Sistema de conocimiento empresarial para contextualizar las recomendaciones de IA.
    Permite cargar PDFs, documentos y crear una base de conocimiento específica del negocio.
    """

    def __init__(self) -> None:
        self.knowledge_data: Dict[str, Any] = {}
        self.load_default_knowledge()

    def load_default_knowledge(self) -> None:
        """Carga conocimiento base del negocio de moda orientado a LATAM."""
        self.knowledge_data = {
            # Tendencias genéricas (se combinan con temporada calculada)
            "seasonal_trends": {
                "primavera": ["colores vivos/pastel", "tejidos ligeros", "capa fina", "estampados florales"],
                "verano": ["líneas resort", "shorts", "camisetas", "sandalias", "sombreros"],
                "otoño": ["tonos tierra", "suéteres", "botas", "chaquetas ligeras"],
                "invierno": ["capas térmicas", "abrigos", "bufandas", "botas"],
                "lluvias": ["impermeables", "botas water-proof", "secado rápido", "capas ligeras"],
                "seca": ["prendas transpirables", "tejidos frescos", "looks urbanos"],
            },
            "cross_sell_rules": {
                "camisas": ["pantalones", "chaquetas", "accesorios"],
                "pantalones": ["camisas", "cinturones", "zapatos"],
                "vestidos": ["zapatos", "bolsos", "joyería"],
                "zapatos": ["medias", "cuidado de calzado", "plantillas"],
            },
            "customer_segments": {
                "joven_trendy": {
                    "age_range": "18-25",
                    "interests": ["tendencias", "redes sociales", "fast fashion"],
                    "channels": ["instagram", "tiktok", "email"],
                    "price_sensitivity": "alta",
                },
                "profesional": {
                    "age_range": "26-40",
                    "interests": ["calidad", "versatilidad", "trabajo"],
                    "channels": ["email", "linkedin", "whatsapp"],
                    "price_sensitivity": "media",
                },
                "maduro_premium": {
                    "age_range": "40+",
                    "interests": ["calidad premium", "durabilidad", "comodidad"],
                    "channels": ["email", "llamada", "presencial"],
                    "price_sensitivity": "baja",
                },
            },
            "churn_patterns": {
                "alta_frecuencia": "Cliente que compra semanalmente y deja de hacerlo",
                "estacional": "Cliente que compra en temporadas específicas",
                "ocasional": "Cliente que compra para eventos especiales",
                "price_sensitive": "Cliente que solo compra con descuentos",
            },
            "retention_strategies": {
                "descuento_progresivo": "Aumentar descuento según días sin comprar",
                "bundle_personalizado": "Agrupar productos basado en historial",
                "early_access": "Acceso anticipado a nuevas colecciones",
                "loyalty_points": "Puntos extra en categorías favoritas",
            },
        }

    def add_pdf_knowledge(self, pdf_content: bytes, category: str = "general") -> str:
        """Extrae texto de PDF y lo añade a la base de conocimiento."""
        if PyPDF2 is None:
            raise RuntimeError(
                "PyPDF2 no está instalado. Instálalo con 'pip install PyPDF2' para cargar PDFs."
            )
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += (page.extract_text() or "") + "\n"

            # Crear hash único para el documento
            doc_hash = hashlib.md5(pdf_content).hexdigest()[:8]

            # Almacenar en knowledge base
            if category not in self.knowledge_data:
                self.knowledge_data[category] = {}

            self.knowledge_data[category][f"document_{doc_hash}"] = {
                "content": text_content,
                "type": "pdf",
                "added_at": datetime.now().isoformat(),
                "summary": self._extract_key_points(text_content),
            }

            logger.info(
                f"PDF añadido a knowledge base: categoría '{category}', hash {doc_hash}"
            )
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
            "summary": self._extract_key_points(content),
        }

        return doc_id

    def _extract_key_points(self, text: str) -> List[str]:
        """Extrae puntos clave de un texto (versión básica)."""
        lines = text.split("\n")
        key_points: List[str] = []

        for line in lines:
            line = line.strip()
            if 20 < len(line) < 200:
                if any(
                    word in line.lower()
                    for word in [
                        "importante",
                        "clave",
                        "estrategia",
                        "objetivo",
                        "resultado",
                        "tendencia",
                        "recomendación",
                    ]
                ):
                    key_points.append(line)
                elif re.search(r"\d+%|\d+\.\d+", line):
                    key_points.append(line)

        return key_points[:10]

    def get_context_for_client(self, client_data: Dict[str, Any], category: Optional[str] = None) -> str:
        """Obtiene contexto relevante de la knowledge base para un cliente (LATAM-aware)."""
        relevant_context: List[str] = []

        # Temporada LATAM según país/ciudad
        country_or_city = client_data.get("country") or client_data.get("city") or ""
        season = get_latam_season(country_or_city=country_or_city)
        seasonal_trends = self.knowledge_data.get("seasonal_trends", {}).get(season, [])
        if seasonal_trends:
            relevant_context.append(f"Tendencias actuales ({season}): {', '.join(seasonal_trends)}")

        # Contexto de segmento
        segment = client_data.get("segment", "general")
        if segment in self.knowledge_data.get("customer_segments", {}):
            segment_info = self.knowledge_base_safe_json(self.knowledge_data["customer_segments"][segment])
            relevant_context.append(f"Perfil del segmento '{segment}': {segment_info}")

        # Cross-sell basado en categoría favorita
        fav_category = str(client_data.get("last_category", "")).lower()
        cross_sell = self.knowledge_data.get("cross_sell_rules", {}).get(fav_category, [])
        if cross_sell:
            relevant_context.append(f"Productos complementarios a {fav_category}: {', '.join(cross_sell)}")

        # Documentos específicos de la categoría si se proporciona
        if category and category in self.knowledge_data:
            for _doc_id, doc_data in self.knowledge_data[category].items():
                if isinstance(doc_data, dict) and doc_data.get("summary"):
                    relevant_context.append(
                        f"Conocimiento empresarial: {', '.join(doc_data['summary'][:3])}"
                    )

        return "\n".join(relevant_context)

    @staticmethod
    def knowledge_base_safe_json(data: Dict[str, Any]) -> str:
        try:
            return json.dumps(data, ensure_ascii=False)
        except Exception:
            return str(data)


class OpenAIService:
    """
    Servicio avanzado para generar recomendaciones con IA contextualizada.
    Integra knowledge base empresarial y prompts optimizados.
    """

    def __init__(self) -> None:
        self.client = None
        self._model = "gpt-4o-mini"
        self.knowledge_base = KnowledgeBase()

        # Buscar API key
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NEXT_PUBLIC_OPENAI_KEY")
        if not api_key:
            logger.error("OpenAI API key no encontrada. Este servicio requiere IA (sin fallbacks).")
            return

        try:
            from openai import OpenAI  # type: ignore
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client inicializado correctamente")
        except ImportError:
            logger.error("SDK de OpenAI no encontrado. Instala: pip install openai>=1.0")
            self.client = None
        except Exception as e:
            logger.error(f"Error inicializando OpenAI client: {e}")
            self.client = None

    def _ensure_available(self) -> None:
        """Requiere IA disponible (sin fallback)."""
        if self.client is None:
            raise RuntimeError(
                "Servicio de IA no disponible: configure OPENAI_API_KEY e instale el SDK 'openai'."
            )

    def _safe_json_parse(self, text: str) -> Any:
        """Parsea JSON de forma segura."""
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Buscar bloques JSON
        array_match = re.search(r"\[.*\]", text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

        object_match = re.search(r"\{.*\}", text, re.DOTALL)
        if object_match:
            try:
                return json.loads(object_match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"No se pudo parsear JSON de: {text[:200]}...")
        raise json.JSONDecodeError("No se encontró JSON válido", text, 0)

    def _prepare_basic_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Contexto básico del cliente."""
        name = client_data.get("name", "Cliente")
        churn_score = client_data.get("churn_score", 0)
        segment = client_data.get("segment", "general")
        last_purchase_days = client_data.get("last_purchase_days", 999)

        # Análisis de compras
        total_spent = sum(float(p.get("total_price", 0) or 0) for p in purchase_history)
        avg_ticket = total_spent / len(purchase_history) if purchase_history else 0

        # Categorías más compradas
        categories: Dict[str, int] = {}
        for purchase in purchase_history:
            items = purchase.get("items", []) or []
            for item in items:
                category = self._infer_category(str(item.get("name", "")))
                categories[category] = categories.get(category, 0) + 1

        top_category = max(categories.keys(), key=lambda k: categories[k]) if categories else "general"

        return (
            f"- Nombre: {name}\n"
            f"- Segmento: {segment}\n"
            f"- Riesgo de churn: {churn_score}%\n"
            f"- Días sin comprar: {last_purchase_days}\n"
            f"- Total gastado: ${total_spent:.2f}\n"
            f"- Ticket promedio: ${avg_ticket:.2f}\n"
            f"- Compras realizadas: {len(purchase_history)}\n"
            f"- Categoría favorita: {top_category}\n"
            f"- Distribución de categorías: {dict(list(categories.items())[:3])}"
        )

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
        months: List[int] = []
        for purchase in purchase_history:
            if purchase.get("purchased_at"):
                try:
                    month = datetime.fromisoformat(str(purchase["purchased_at"])).month
                    months.append(month)
                except Exception:
                    pass

        seasonal_pattern = "No identificado"
        if months:
            most_common_month = max(set(months), key=months.count)
            # Clasificación LATAM simple
            if 12 <= most_common_month or most_common_month <= 2:
                seasonal_pattern = "Alta de fin de año/verano LATAM"
            elif 5 <= most_common_month <= 10:
                seasonal_pattern = "Picos en temporada de lluvias/tropical"

        # Sensibilidad al precio
        prices = [float(p.get("total_price", 0) or 0) for p in purchase_history]
        avg_price = sum(prices) / len(prices) if prices else 0
        if avg_price > 100:
            price_sensitivity = "baja"
        elif avg_price > 50:
            price_sensitivity = "media"
        else:
            price_sensitivity = "alta"

        return (
            f"- Frecuencia de compra: {frequency}\n"
            f"- Patrón estacional: {seasonal_pattern}\n"
            f"- Sensibilidad al precio: {price_sensitivity}\n"
            f"- Ticket promedio: ${avg_price:.2f}\n"
            f"- Última compra: hace {client_data.get('last_purchase_days', 999)} días"
        )

    def _infer_category(self, item_name: str) -> str:
        """Infiere la categoría de un producto basado en su nombre."""
        item_lower = item_name.lower()

        if any(word in item_lower for word in ["camisa", "blusa", "camiseta", "polo", "top"]):
            return "camisas_tops"
        if any(word in item_lower for word in ["pantalon", "pantalón", "jean", "bermuda", "short", "leggin", "legging"]):
            return "pantalones"
        if any(word in item_lower for word in ["vestido", "falda"]):
            return "vestidos_faldas"
        if any(word in item_lower for word in ["zapato", "sandalia", "bota", "tenis", "sneaker"]):
            return "calzado"
        if any(word in item_lower for word in ["chaqueta", "abrigo", "sueter", "suéter", "cardigan", "cárdigan"]):
            return "abrigo"
        if any(word in item_lower for word in ["bolso", "cartera", "mochila"]):
            return "bolsos"
        if any(word in item_lower for word in ["collar", "pulsera", "anillo", "arete", "pendiente"]):
            return "accesorios"
        return "otros"

    def _prepare_enhanced_client_context(self, client_data: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
        """Prepara contexto enriquecido del cliente con knowledge base (LATAM-aware)."""
        basic_context = self._prepare_basic_context(client_data, purchase_history)
        business_context = self.knowledge_base.get_context_for_client(client_data)
        behavior_analysis = self._analyze_customer_behavior(client_data, purchase_history)
        return (
            "PERFIL DEL CLIENTE:\n"
            f"{basic_context}\n\n"
            "CONTEXTO EMPRESARIAL:\n"
            f"{business_context}\n\n"
            "ANÁLISIS DE COMPORTAMIENTO:\n"
            f"{behavior_analysis}"
        )

    # ---------------------- Métodos IA (sin fallback) ---------------------- #

    def generate_client_recommendations(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Genera recomendaciones personalizadas con IA contextualizada (100% IA)."""
        self._ensure_available()

        context = self._prepare_enhanced_client_context(client_data, purchase_history)

        # Temporada LATAM para incluir en el prompt
        season = get_latam_season(country_or_city=client_data.get("country") or client_data.get("city"))

        prompt = f"""Eres María, una experta consultora en marketing de retención con 15 años de experiencia en retail de moda LATAM.
Has ayudado a cientos de marcas a reducir el churn y aumentar el CLV. Ajusta lenguaje y ejemplos a LATAM.

TEMPORADA_COMERCIAL_ACTUAL: {season}

SITUACIÓN:
{context}

TU MISIÓN:
Genera 3-4 recomendaciones ultra-específicas y accionables para este cliente. Cada recomendación debe ser tan personalizada que el cliente sienta que fue diseñada exclusivamente para él/ella.

CRITERIOS DE EXCELENCIA:
1. ESPECÍFICO: Menciona productos, categorías, colores o estilos concretos
2. URGENTE: Define timeframes claros (24h, 7 días, etc.)
3. PERSONAL: Referencias directas a su historial de compra
4. MEDIBLE: Incluye métricas esperadas cuando sea relevante

FORMATO DE RESPUESTA (JSON ESTRICTO):
[
  {{
    "type": "discount_targeted|vip_treatment|bundle_offer|early_access|personal_shopper",
    "title": "Título que capture atención (máx 60 caracteres)",
    "description": "Descripción específica mencionando productos/categorías de su historial y temporada LATAM",
    "urgency": "crítica|alta|media",
    "channel": "email_personalizado|whatsapp_vip|llamada_personal|sms_exclusivo",
    "timing": "inmediato|dentro_24h|esta_semana|proximos_7dias",
    "expected_conversion": "15-25%|10-15%|5-10%",
    "reasoning": "Por qué esta recomendación es perfecta para ESTE cliente específico"
  }}
]

Responde SOLO con el JSON, sin explicaciones adicionales."""
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres María, consultora experta en retención en fashion retail para LATAM."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1200,
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            recommendations = self._safe_json_parse(content)

            # Normalización
            if isinstance(recommendations, dict):
                recommendations = [recommendations]
            if not isinstance(recommendations, list):
                raise ValueError("La IA no devolvió una lista JSON válida de recomendaciones.")

            valid_recs: List[Dict[str, Any]] = []
            for rec in recommendations:
                if isinstance(rec, dict) and "type" in rec and "description" in rec:
                    rec.setdefault("urgency", "media")
                    rec.setdefault("channel", "email_personalizado")
                    rec.setdefault("reasoning", "Recomendación basada en análisis de perfil y temporada LATAM")
                    valid_recs.append(rec)

            if not valid_recs:
                raise ValueError("La IA devolvió un JSON sin elementos válidos.")
            return valid_recs

        except Exception as e:
            logger.error(f"Error generando recomendaciones con OpenAI: {e}")
            raise

    def generate_client_suggestions(
        self,
        client_data: Dict[str, Any],
        purchase_history: List[Dict[str, Any]],
        days_since_last: int,
    ) -> List[Dict[str, Any]]:
        """Genera sugerencias específicas con IA contextualizada (100% IA)."""
        self._ensure_available()

        context = self._prepare_enhanced_client_context(client_data, purchase_history)
        season = get_latam_season(country_or_city=client_data.get("country") or client_data.get("city"))
        estado = "🔴 CRÍTICO" if days_since_last > 90 else "🟡 EN RIESGO" if days_since_last > 45 else "🟢 ACTIVO"

        prompt = f"""Eres Carlos, consultor senior de experiencia del cliente para fashion retail en LATAM.
Optimiza AOV y NPS, cuidando coherencia con temporada LATAM '{season}'.

CLIENTE ANALIZADO:
{context}

CONTEXTO ADICIONAL:
- Días desde última compra: {days_since_last}
- Estado del cliente: {estado}

TU OBJETIVO:
Crear 2-3 sugerencias que mejoren la experiencia y fidelicen al cliente a largo plazo.

ENFOQUE ESTRATÉGICO:
- Si es cliente crítico (>90 días): REACTIVACIÓN con alto valor percibido
- En riesgo (45-90 días): RETENCIÓN con relevancia personal
- Activo (<45 días): CRECIMIENTO con upsell/cross-sell

FORMATO JSON ESTRICTO:
[
  {{
    "type": "product_bundle|experience_upgrade|vip_program|personal_styling|seasonal_collection",
    "title": "Título atractivo (máx 50 caracteres)",
    "description": "Descripción detallada con productos/categorías específicas y referencia a temporada '{season}'",
    "value_proposition": "¿Por qué es irresistible para ESTE cliente?",
    "implementation": "Pasos ejecutables en tienda/online",
    "priority": "crítica|alta|media",
    "expected_revenue_increase": "+15-30%|+10-20%|+5-15%",
    "timeline": "inmediato|1_semana|1_mes"
  }}
]

Responde SOLO con JSON válido."""
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres Carlos, consultor senior de CX para moda en LATAM."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=900,
                temperature=0.8,
            )
            content = response.choices[0].message.content.strip()
            suggestions = self._safe_json_parse(content)

            if isinstance(suggestions, dict):
                suggestions = [suggestions]
            if not isinstance(suggestions, list):
                raise ValueError("La IA no devolvió una lista JSON válida de sugerencias.")

            valid_suggestions: List[Dict[str, Any]] = []
            for sug in suggestions:
                if isinstance(sug, dict) and "title" in sug and "description" in sug:
                    sug.setdefault("priority", "media")
                    valid_suggestions.append(sug)

            if not valid_suggestions:
                raise ValueError("La IA devolvió un JSON sin elementos válidos.")
            return valid_suggestions

        except Exception as e:
            logger.error(f"Error generando sugerencias con OpenAI: {e}")
            raise

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Análisis de sentimiento con contexto de moda LATAM (100% IA)."""
        self._ensure_available()

        prompt = f"""Eres un analista experto en customer feedback para retail de moda en LATAM.

TEXTO A ANALIZAR:
\"\"\"{text}\"\"\"

Devuelve SOLO JSON:
{{
  "sentiment": "very_positive|positive|neutral|negative|very_negative",
  "confidence": 0.XX,
  "emotions": ["joy","trust","excitement","disappointment","frustration","anger"],
  "key_phrases": ["frases importantes extraídas"],
  "customer_intent": "compra|queja|consulta|devolución|elogio|sugerencia",
  "urgency_level": "critico|alto|medio|bajo",
  "recommended_action": "respuesta_inmediata|seguimiento_24h|respuesta_estandar|archivar",
  "business_impact": "alto_valor|oportunidad_mejora|cliente_satisfecho|riesgo_churn"
}}"""
        try:
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "Eres un analista experto en customer sentiment para retail en LATAM."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.2,
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
            raise

    # --------- Pasarela para conocimiento empresarial --------- #

    def add_business_knowledge(self, content: str, title: str, category: str = "general") -> str:
        """Añade conocimiento empresarial al sistema."""
        return self.knowledge_base.add_text_knowledge(content, title, category)

    def add_pdf_knowledge(self, pdf_content: bytes, category: str = "general") -> str:
        """Añade conocimiento desde PDF."""
        return self.knowledge_base.add_pdf_knowledge(pdf_content, category)

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Obtiene resumen del conocimiento disponible."""
        summary: Dict[str, Any] = {}
        for category, docs in self.knowledge_base.knowledge_data.items():
            if isinstance(docs, dict):
                summary[category] = {
                    "documents": len(docs),
                    "titles": [
                        (doc.get("title", doc_id) if isinstance(doc, dict) else str(doc_id))
                        for doc_id, doc in docs.items()
                    ],
                }
            else:
                summary[category] = "Built-in knowledge"
        return summary
