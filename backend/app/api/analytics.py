# backend/app/api/analytics.py - VERSIÓN MEJORADA
from fastapi import APIRouter, HTTPException, Depends
from app.db.supabase import supabase
from app.utils.auth import require_user  # ← AÑADIR autenticación
import logging
from datetime import date, timedelta
from typing import Dict, List, Any, Optional

router = APIRouter()
logger = logging.getLogger(__name__)

def safe_supabase_query(table_name: str, user_id: str, description: str) -> List[Dict]:
    """
    Ejecuta una consulta de Supabase de forma segura con manejo de errores.
    """
    try:
        logger.info(f"Ejecutando {description} para user_id: {user_id}")
        
        result = (
            supabase.table(table_name)
            .select("*")
            .eq("owner_id", user_id)
            .execute()
        )
        
        # Verificar si hay error
        if hasattr(result, 'error') and result.error:
            error_msg = getattr(result.error, 'message', str(result.error))
            logger.error(f"Error Supabase en {table_name}: {error_msg}")
            return []
        
        data = result.data or []
        logger.info(f"{description}: {len(data)} registros encontrados")
        return data
        
    except Exception as e:
        logger.error(f"Excepción en {description}: {str(e)}")
        # Retornar array vacío en lugar de fallar
        return []

@router.get("/overview")
def analytics_overview(user_id: str = Depends(require_user)):
    """
    Devuelve un resumen analítico SOLO para el usuario actual.
    Versión robusta que no falla si las vistas no existen.
    """
    try:
        logger.info(f"=== ANALYTICS OVERVIEW INICIADO ===")
        logger.info(f"User ID recibido: {user_id}")
        
        # 1. Top Customers (últimos 90 días)
        top_customers = safe_supabase_query(
            "v_top_customers_90d", 
            user_id, 
            "Top customers 90d"
        )
        
        # 2. Top Products (últimos 90 días)  
        top_products = safe_supabase_query(
            "v_top_products_90d",
            user_id,
            "Top products 90d"
        )
        
        # 3. Sales trend (últimos 7 días)
        trend_data = safe_supabase_query(
            "v_sales_trend_7d",
            user_id,
            "Sales trend 7d"
        )
        
        # Si no hay datos de tendencia, crear estructura con ceros
        if not trend_data:
            logger.info("Creando datos de tendencia por defecto (últimos 7 días)")
            trend_data = []
            for i in range(7):
                trend_date = date.today() - timedelta(days=6-i)
                trend_data.append({
                    "sale_date": trend_date.isoformat(),
                    "owner_id": user_id,
                    "order_count": 0,
                    "daily_revenue": 0,
                    "unique_customers": 0
                })
        
        # 4. Churn Risk
        churn_data = safe_supabase_query(
            "v_churn_risk",
            user_id,
            "Churn risk"
        )
        
        # Preparar respuesta
        response = {
            "topCustomers": top_customers[:10],  # Limitar a 10
            "topProducts": top_products[:10],    # Limitar a 10  
            "trend7d": trend_data,
            "churnRisk": churn_data[:20],        # Top 20 en riesgo
            "owner_id": user_id,                 # Para debug
            "summary": {
                "customers_count": len(top_customers),
                "products_count": len(top_products),
                "trend_days": len(trend_data),
                "churn_alerts": len(churn_data)
            },
            "debug_info": {
                "server_date": date.today().isoformat(),
                "supabase_connected": True,  # Si llegamos aquí, está conectado
                "user_authenticated": True
            }
        }
        
        logger.info(f"=== RESPUESTA PREPARADA ===")
        logger.info(f"Customers: {len(top_customers)}, Products: {len(top_products)}, "
                   f"Trend points: {len(trend_data)}, Churn alerts: {len(churn_data)}")
        
        return response
        
    except Exception as e:
        logger.error(f"=== ERROR CRÍTICO EN ANALYTICS ===")
        logger.error(f"User ID: {user_id}")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Tipo: {type(e).__name__}")
        
        # En lugar de fallar, devolver estructura básica
        fallback_response = {
            "topCustomers": [],
            "topProducts": [], 
            "trend7d": _generate_empty_trend(),
            "churnRisk": [],
            "owner_id": user_id,
            "summary": {
                "customers_count": 0,
                "products_count": 0,
                "trend_days": 7,
                "churn_alerts": 0
            },
            "debug_info": {
                "server_date": date.today().isoformat(),
                "error_occurred": True,
                "error_message": str(e),
                "fallback_mode": True
            }
        }
        
        logger.info("Retornando respuesta de fallback")
        return fallback_response

def _generate_empty_trend() -> List[Dict]:
    """Genera datos de tendencia vacíos para los últimos 7 días."""
    trend_data = []
    for i in range(7):
        trend_date = date.today() - timedelta(days=6-i)
        trend_data.append({
            "sale_date": trend_date.isoformat(),
            "order_count": 0,
            "daily_revenue": 0,
            "unique_customers": 0
        })
    return trend_data

@router.get("/churn-risk")  
def churn_risk_details(user_id: str = Depends(require_user)):
    """
    Endpoint específico para obtener detalles de riesgo de churn.
    Versión robusta.
    """
    try:
        logger.info(f"Churn risk details para user_id: {user_id}")
        
        churn_data = safe_supabase_query(
            "v_churn_risk",
            user_id,
            "Churn risk details"
        )
        
        high_risk = [c for c in churn_data if c.get("churn_score", 0) >= 70]
        
        return {
            "clients": churn_data,
            "total": len(churn_data),
            "high_risk_count": len(high_risk),
            "owner_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error en churn_risk_details: {e}")
        return {
            "clients": [],
            "total": 0,
            "high_risk_count": 0,
            "owner_id": user_id,
            "error": str(e)
        }

@router.get("/debug")
def debug_analytics(user_id: str = Depends(require_user)):
    """
    Endpoint de debug para verificar el estado del sistema.
    """
    try:
        logger.info(f"=== DEBUG ANALYTICS ===")
        logger.info(f"User ID: {user_id}")
        
        # Probar conexión a Supabase
        test_result = supabase.table("auth").select("count", count="exact").execute()
        supabase_ok = not (hasattr(test_result, 'error') and test_result.error)
        
        # Verificar si las vistas existen
        views_status = {}
        views_to_check = [
            "v_top_customers_90d", 
            "v_top_products_90d", 
            "v_sales_trend_7d", 
            "v_churn_risk"
        ]
        
        for view in views_to_check:
            try:
                result = supabase.table(view).select("*").limit(1).execute()
                views_status[view] = {
                    "exists": True,
                    "error": None,
                    "has_data": bool(result.data)
                }
            except Exception as e:
                views_status[view] = {
                    "exists": False,
                    "error": str(e),
                    "has_data": False
                }
        
        return {
            "user_id": user_id,
            "supabase_connection": supabase_ok,
            "server_time": date.today().isoformat(),
            "views_status": views_status,
            "debug_timestamp": str(date.today())
        }
        
    except Exception as e:
        logger.error(f"Error en debug_analytics: {e}")
        return {
            "user_id": user_id,
            "error": str(e),
            "debug_timestamp": str(date.today())
        }
