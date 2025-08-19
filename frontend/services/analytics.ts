// services/analytics.ts - VERSIÓN CORREGIDA
// Añade manejo de errores y debugging

import { fetcher } from "./fetcher";

export type SalesPoint = { day: string; revenue: number };

export type TopCustomer = {
  client_id: number;
  client_name: string;
  email: string | null;
  orders_count: number;
  total_spent: number;
};

export type TopProduct = {
  item_id: number;
  item_name: string;
  units_sold: number;
  revenue: number;
};

export type ChurnRisk = {
  client_id: number;
  name: string;
  email: string | null;
  last_purchase_at: string | null;
  churn_score: number;
};

export type Overview = {
  topCustomers: TopCustomer[];
  topProducts: TopProduct[];
  trend7d: SalesPoint[];
  churnRisk: ChurnRisk[];
  owner_id?: string; // Para debugging
  summary?: {
    customers_count: number;
    products_count: number;
    trend_days: number;
    churn_alerts: number;
  };
};

// 🔧 FUNCIÓN PRINCIPAL MEJORADA CON DEBUGGING
export async function getOverview(): Promise<Overview> {
  try {
    console.log("[analytics] Llamando a /analytics/overview...");
    
    const { data } = await fetcher.get<Overview>("/analytics/overview");
    
    console.log("[analytics] Respuesta recibida:", {
      hasData: !!data,
      topCustomers: data?.topCustomers?.length || 0,
      topProducts: data?.topProducts?.length || 0,
      trend7d: data?.trend7d?.length || 0,
      churnRisk: data?.churnRisk?.length || 0,
      owner_id: data?.owner_id,
      summary: data?.summary
    });
    
    // Normaliza para robustez
    const normalized = {
      topCustomers: Array.isArray(data?.topCustomers) ? data.topCustomers : [],
      topProducts: Array.isArray(data?.topProducts) ? data.topProducts : [],
      trend7d: Array.isArray(data?.trend7d) ? data.trend7d : [],
      churnRisk: Array.isArray(data?.churnRisk) ? data.churnRisk : [],
      owner_id: data?.owner_id,
      summary: data?.summary
    };
    
    return normalized;
    
  } catch (error: any) {
    console.error("[analytics] Error completo:", {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      config: {
        url: error.config?.url,
        method: error.config?.method,
        headers: error.config?.headers
      }
    });
    
    // Re-lanzar el error para que React Query lo maneje
    throw error;
  }
}

// Helpers que preservan la API previa:
export async function getSalesTrend7d(): Promise<SalesPoint[]> {
  const o = await getOverview();
  return o.trend7d;
}

export async function getTopCustomers90d(limit = 5): Promise<TopCustomer[]> {
  const o = await getOverview();
  return o.topCustomers.slice(0, limit);
}

export async function getTopProducts90d(limit = 5): Promise<TopProduct[]> {
  const o = await getOverview();
  return o.topProducts.slice(0, limit);
}

export async function getChurnRisk(limit = 5): Promise<ChurnRisk[]> {
  const o = await getOverview();
  return o.churnRisk.slice(0, limit);
}

// 🆕 FUNCIÓN DE DEBUGGING - llamar desde la consola
export async function debugAnalytics() {
  try {
    console.log("=== DEBUG ANALYTICS ===");
    
    // Verificar token
    const auth = localStorage.getItem('auth');
    console.log("Auth en localStorage:", auth ? JSON.parse(auth) : null);
    
    // Probar endpoint
    const result = await getOverview();
    console.log("Resultado exitoso:", result);
    
    return result;
  } catch (error) {
    console.error("Error en debug:", error);
    return null;
  }
}
