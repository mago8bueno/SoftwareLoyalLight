# backend/app/api/ai.py  
from fastapi import APIRouter, HTTPException, Query  
from typing import Any, Dict, List, Optional, Union  
from app.db.supabase import supabase  
from app.services.openai_service import OpenAIService  
import logging  
  
router = APIRouter()  
openai_service = OpenAIService()  
  
logger = logging.getLogger(__name__)  
  
  
@router.get(  
    "/recommendations",  
    summary="Recomendaciones IA con OpenAI",  
    tags=["ai"],  
)  
def recommendations(  
    client_id: Optional[Union[str, int]] = Query(  
        None, description="ID de cliente (opcional; admite UUID o entero)"  
    ),  
    limit: int = Query(5, ge=1, le=50),  
    tenant_id: Optional[str] = Query(  
        None,  
        description="Tenant opcional para filtrar datos (si tu schema es multi-tenant)",  
    ),  
) -> Dict[str, Any]:  
    """  
    Genera recomendaciones usando OpenAI GPT basadas en el perfil del cliente.  
    - Si pasas client_id => recomendaciones personalizadas para ese cliente.  
    - Si NO pasas client_id => devuelve top clientes en riesgo con recomendaciones.  
    """  
    try:  
        if client_id is not None:  
            # Obtener datos del cliente  
            q = supabase.table("v_churn_risk").select("*").eq("client_id", client_id).limit(1)  
            if tenant_id:  
                q = q.eq("tenant_id", tenant_id)  
  
            res = q.execute()  
            if not res.data:  
                raise HTTPException(status_code=404, detail="Cliente no encontrado en v_churn_risk")  
  
            client_data = res.data[0]  
              
            # Obtener historial de compras  
            purchases_q = (  
                supabase.table("purchases")  
                .select("*, items(*)")  
                .eq("client_id", client_id)  
                .order("created_at", desc=True)  
                .limit(10)  
            )  
            if tenant_id:  
                purchases_q = purchases_q.eq("tenant_id", tenant_id)  
              
            purchases_res = purchases_q.execute()  
            purchase_history = purchases_res.data or []  
  
            # Generar recomendaciones con IA  
            ai_recommendations = openai_service.generate_client_recommendations(  
                client_data, purchase_history  
            )  
  
            return {  
                "client": {  
                    "id": client_data["client_id"],  
                    "name": client_data.get("name"),  
                    "email": client_data.get("email"),  
                    "churn_score": int(client_data.get("churn_score") or 0),  
                },  
                "recommendations": ai_recommendations,  
                "ai_powered": True  
            }  
  
        # Top clientes en riesgo con recomendaciones IA  
        q = supabase.table("v_churn_risk").select("*").order("churn_score", desc=True).limit(limit)  
        if tenant_id:  
            q = q.eq("tenant_id", tenant_id)  
  
        res = q.execute()  
        items: List[Dict[str, Any]] = []  
          
        for client_data in res.data or []:  
            # Obtener historial limitado para cada cliente  
            purchases_q = (  
                supabase.table("purchases")  
                .select("*, items(*)")  
                .eq("client_id", client_data["client_id"])  
                .order("created_at", desc=True)  
                .limit(5)  
            )  
            if tenant_id:  
                purchases_q = purchases_q.eq("tenant_id", tenant_id)  
              
            purchases_res = purchases_q.execute()  
            purchase_history = purchases_res.data or []  
  
            # Generar recomendaciones con IA  
            ai_recommendations = openai_service.generate_client_recommendations(  
                client_data, purchase_history  
            )  
  
            items.append({  
                "client": {  
                    "id": client_data["client_id"],  
                    "name": client_data.get("name"),  
                    "email": client_data.get("email"),  
                    "churn_score": int(client_data.get("churn_score") or 0),  
                },  
                "recommendations": ai_recommendations,  
                "ai_powered": True  
            })  
              
        return {"items": items}  
  
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"[/ai/recommendations] error: {repr(e)}")  
        raise HTTPException(status_code=500, detail="No se pudieron calcular recomendaciones")  
  
  
@router.get(  
    "/clients/{client_id}/suggestions",  
    summary="Sugerencias IA personalizadas con OpenAI",  
    tags=["ai"],  
)  
def client_suggestions(  
    client_id: Union[str, int],  
    tenant_id: Optional[str] = Query(  
        None, description="Tenant opcional para filtrar compras del cliente"  
    ),  
) -> Dict[str, Any]:  
    """  
    Genera sugerencias personalizadas usando OpenAI basadas en el historial completo del cliente.  
    """  
    try:  
        # Obtener datos del cliente  
        client_q = supabase.table("clients").select("*").eq("id", client_id).limit(1)  
        if tenant_id:  
            client_q = client_q.eq("tenant_id", tenant_id)  
          
        client_res = client_q.execute()  
        if not client_res.data:  
            raise HTTPException(status_code=404, detail="Cliente no encontrado")  
          
        client_data = client_res.data[0]  
  
        # Obtener historial completo de compras  
        purchases_q = (  
            supabase.table("purchases")  
            .select("*, items(*)")  
            .eq("client_id", client_id)  
            .order("created_at", desc=True)  
            .limit(20)  
        )  
        if tenant_id:  
            purchases_q = purchases_q.eq("tenant_id", tenant_id)  
  
        purchases_res = purchases_q.execute()  
        purchase_history = purchases_res.data or []  
  
        # Calcular métricas básicas  
        import datetime as dt  
        last_purchase_date = None  
        if purchase_history:  
            last_iso = purchase_history[0]["created_at"]  
            last_purchase_date = dt.datetime.fromisoformat(str(last_iso).replace("Z", "+00:00"))  
            days_since_last = (dt.datetime.now(dt.timezone.utc) - last_purchase_date).days  
        else:  
            days_since_last = 999  
  
        # Generar sugerencias con IA  
        ai_suggestions = openai_service.generate_client_suggestions(  
            client_data, purchase_history, days_since_last  
        )  
  
        return {  
            "client_id": client_id,  
            "last_purchase_days": days_since_last,  
            "total_purchases": len(purchase_history),  
            "suggestions": ai_suggestions,  
            "ai_powered": True  
        }  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"[/ai/clients/{client_id}/suggestions] error: {repr(e)}")  
        raise HTTPException(status_code=500, detail="No se pudieron obtener sugerencias")  
  
  
@router.post(  
    "/analyze-sentiment",  
    summary="Análisis de sentimiento de reseñas/comentarios",  
    tags=["ai"],  
)  
def analyze_sentiment(  
    text: str,  
    client_id: Optional[Union[str, int]] = None  
) -> Dict[str, Any]:  
    """  
    Analiza el sentimiento de un texto usando OpenAI.  
    """  
    try:  
        sentiment_analysis = openai_service.analyze_sentiment(text)  
          
        result = {  
            "text": text,  
            "sentiment": sentiment_analysis,  
            "ai_powered": True  
        }  
          
        if client_id:  
            result["client_id"] = client_id  
              
        return result  
          
    except Exception as e:  
        logger.error(f"[/ai/analyze-sentiment] error: {repr(e)}")  
        raise HTTPException(status_code=500, detail="No se pudo analizar el sentimiento")
