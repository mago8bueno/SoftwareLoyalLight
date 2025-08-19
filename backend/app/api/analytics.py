# backend/app/api/analytics.py
from fastapi import APIRouter, HTTPException, Depends
from app.db.supabase import supabase
from app.utils.auth import require_user  # ← AÑADIR autenticación
import logging
from datetime import date, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/overview")
def analytics_overview(user_id: str = Depends(require_user)):  # ← AÑADIR autenticación
    """
    Devuelve un resumen analítico SOLO para el usuario actual:
    - topCustomers: v_top_customers_90d filtrado por owner_id
    - topProducts:  v_top_products_90d filtrado por owner_id  
    - trend7d:      v_sales_trend_7d filtrado por owner_id
    - churnRisk:    v_churn_risk filtrado por owner_id
    """
    try:
        logger.info(f"analytics_overview for user_id: {user_id}")
        
        # Todas las consultas ahora filtran por owner_id
        top_customers_res = (
            supabase.table("v_top_customers_90d")
            .select("*")
            .eq("owner_id", user_id)  # ← FILTRO CRÍTICO
            .order("total_spent", desc=True)
            .limit(10)  # Limitar resultados
            .execute()
        )
        
        top_products_res = (
            supabase.table("v_top_products_90d")
            .select("*")
            .eq("owner_id", user_id)  # ← FILTRO CRÍTICO
            .order("times_sold", desc=True)
            .limit(10)  # Limitar resultados
            .execute()
        )
        
        trend_res = (
            supabase.table("v_sales_trend_7d")
            .select("*")
            .eq("owner_id", user_id)  # ← FILTRO CRÍTICO
            .order("sale_date", desc=False)
            .execute()
        )
        
        # Si no hay datos de tendencia, crear estructura vacía para el frontend
        if not trend_res.data:
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
            trend_res.data = trend_data
        
        churn_res = (
            supabase.table("v_churn_risk")
            .select("*")
            .eq("owner_id", user_id)  # ← FILTRO CRÍTICO
            .order("churn_score", desc=True)
            .limit(20)  # Top 20 en riesgo
            .execute()
        )

        # Verificar errores en cada consulta
        for res_name, res in [
            ("top_customers", top_customers_res),
            ("top_products", top_products_res), 
            ("trend", trend_res),
            ("churn", churn_res)
        ]:
            if getattr(res, "error", None):
                error_msg = getattr(res.error, "message", str(res.error))
                logger.error(f"Error en {res_name}: {error_msg}")
                # No fallar completamente, usar array vacío
                if not hasattr(res, 'data') or res.data is None:
                    res.data = []

        logger.info(f"Results for user {user_id}: "
                   f"customers={len(top_customers_res.data or [])}, "
                   f"products={len(top_products_res.data or [])}, "
                   f"trend_points={len(trend_res.data or [])}, "
                   f"churn_alerts={len(churn_res.data or [])}")

        return {
            "topCustomers": top_customers_res.data or [],
            "topProducts": top_products_res.data or [],
            "trend7d": trend_res.data or [],
            "churnRisk": churn_res.data or [],
            "owner_id": user_id,  # Para debug
            "summary": {
                "customers_count": len(top_customers_res.data or []),
                "products_count": len(top_products_res.data or []),
                "trend_days": len(trend_res.data or []),
                "churn_alerts": len(churn_res.data or [])
            }
        }
        
    except Exception as e:
        logger.error(f"analytics_overview error for user {user_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error obteniendo analytics: {str(e)}"
        )


@router.get("/churn-risk")  
def churn_risk_details(user_id: str = Depends(require_user)):
    """
    Endpoint específico para obtener detalles de riesgo de churn
    SOLO del usuario actual.
    """
    try:
        res = (
            supabase.table("v_churn_risk")
            .select("*")
            .eq("owner_id", user_id)  # ← FILTRO CRÍTICO
            .order("churn_score", desc=True)
            .execute()
        )
        
        if getattr(res, "error", None):
            error_msg = getattr(res.error, "message", str(res.error))
            raise HTTPException(status_code=400, detail=error_msg)
            
        churn_data = res.data or []
        high_risk = [c for c in churn_data if c.get("churn_score", 0) >= 70]
        
        return {
            "clients": churn_data,
            "total": len(churn_data),
            "high_risk_count": len(high_risk),
            "owner_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"churn_risk_details error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo detalles de churn: {str(e)}"
        )


@router.get("/sales-summary")
def sales_summary(user_id: str = Depends(require_user)):
    """
    Resumen de ventas del usuario actual en diferentes períodos.
    """
    try:
        # Ventas últimos 7 días
        trend_res = (
            supabase.table("v_sales_trend_7d")
            .select("*")
            .eq("owner_id", user_id)
            .execute()
        )
        
        # Ventas últimos 90 días (desde top customers)
        customers_res = (
            supabase.table("v_top_customers_90d")
            .select("total_spent, purchase_count")
            .eq("owner_id", user_id)
            .execute()
        )
        
        trend_data = trend_res.data or []
        customers_data = customers_res.data or []
        
        # Calcular métricas
        last_7d_revenue = sum(float(day.get("daily_revenue", 0)) for day in trend_data)
        last_7d_orders = sum(int(day.get("order_count", 0)) for day in trend_data)
        
        last_90d_revenue = sum(float(c.get("total_spent", 0)) for c in customers_data)
        last_90d_orders = sum(int(c.get("purchase_count", 0)) for c in customers_data)
        
        return {
            "period_7d": {
                "revenue": round(last_7d_revenue, 2),
                "orders": last_7d_orders,
                "avg_order_value": round(last_7d_revenue / max(last_7d_orders, 1), 2)
            },
            "period_90d": {
                "revenue": round(last_90d_revenue, 2), 
                "orders": last_90d_orders,
                "avg_order_value": round(last_90d_revenue / max(last_90d_orders, 1), 2),
                "active_customers": len(customers_data)
            },
            "owner_id": user_id
        }
        
    except Exception as e:
        logger.error(f"sales_summary error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo resumen de ventas: {str(e)}"
        )
