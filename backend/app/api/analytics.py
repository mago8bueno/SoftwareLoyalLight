# app/api/analytics.py
# Endpoints de analítica que leen de vistas Postgres creadas en Supabase

from fastapi import APIRouter, HTTPException
from app.db.supabase import supabase

router = APIRouter()

@router.get("/overview")
def analytics_overview():
    """
    Devuelve un resumen con:
    - topCustomers: v_top_customers_90d
    - topProducts:  v_top_products_90d
    - trend7d:      v_sales_trend_7d
    - churnRisk:    v_churn_risk
    """
    try:
        top_customers_res = supabase.table("v_top_customers_90d").select("*").execute()
        top_products_res  = supabase.table("v_top_products_90d").select("*").execute()
        trend_res         = supabase.table("v_sales_trend_7d").select("*").execute()
        churn_res         = supabase.table("v_churn_risk").select("*").execute()

        return {
            "topCustomers": top_customers_res.data or [],
            "topProducts": top_products_res.data or [],
            "trend7d": trend_res.data or [],
            "churnRisk": churn_res.data or [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"analytics_overview error: {e}")
