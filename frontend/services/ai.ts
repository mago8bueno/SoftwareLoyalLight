// services/ai.ts
import { fetcher } from './fetcher';

/** Soportar IDs numéricos o string (UUID) */
export type ID = string | number;

export type ClientSuggestion = {
  client_id: ID;
  churn_score: number;
  last_purchase_days: number;
  top_item_id: number | string | null;
  suggestions: { type: string; text: string }[];
};

/**
 * Sugerencias por cliente.
 * - clientId puede ser number o string (UUID)
 * - tenantId opcional por si filtras por tenant en el backend
 */
export async function getClientSuggestions(
  clientId: ID,
  opts?: { tenantId?: string },
): Promise<ClientSuggestion> {
  const url = `/ai/clients/${encodeURIComponent(String(clientId))}/suggestions`;
  const { data } = await fetcher.get<ClientSuggestion>(url, {
    params: opts?.tenantId ? { tenant_id: opts.tenantId } : undefined,
  });
  return data;
}

/** -------- Opcional: listado de clientes en riesgo con recomendaciones ---------- */

export type AIItem = {
  client: { id: ID; name?: string; email?: string; churn_score: number };
  recommendations: { type: string; text: string }[];
};

/**
 * Top clientes en riesgo (reglas simples).
 * - Si pasas clientId, devuelve solo ese cliente.
 * - tenantId opcional.
 */
export async function getRecommendations(params?: {
  limit?: number;
  clientId?: ID;
  tenantId?: string;
}): Promise<
  { items: AIItem[] } | { client: AIItem['client']; recommendations: AIItem['recommendations'] }
> {
  const { limit = 5, clientId, tenantId } = params || {};

  const { data } = await fetcher.get('/ai/recommendations', {
    params: {
      limit,
      client_id: clientId != null ? String(clientId) : undefined,
      tenant_id: tenantId,
    },
  });

  // El backend devuelve { items: [...] } o { client, recommendations } si pasas client_id
  return data;
}
