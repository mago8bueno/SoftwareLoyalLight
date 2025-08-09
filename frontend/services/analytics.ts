// services/analytics.ts
// Analítica: un único endpoint backend (/analytics/overview) y helpers que
// exponen las partes (trend7d, topCustomers, topProducts, churnRisk).

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
};

// Llama al único endpoint válido del backend
export async function getOverview(): Promise<Overview> {
  const { data } = await fetcher.get<Overview>("/analytics/overview");
  // Normaliza para robustez
  return {
    topCustomers: Array.isArray(data?.topCustomers) ? data.topCustomers : [],
    topProducts: Array.isArray(data?.topProducts) ? data.topProducts : [],
    trend7d: Array.isArray(data?.trend7d) ? data.trend7d : [],
    churnRisk: Array.isArray(data?.churnRisk) ? data.churnRisk : [],
  };
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
