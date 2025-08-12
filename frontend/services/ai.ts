// frontend/services/ai.ts
import { fetcher } from './fetcher';

export type ID = string | number;

export type AISuggestion = {
  type: string;
  title?: string;
  description: string;          // mandatory
  priority?: string;
  expected_impact?: string;
};

export type ClientSuggestion = {
  client_id: ID;
  churn_score: number;
  last_purchase_days: number;
  top_item_id: number | string | null;
  suggestions: AISuggestion[];  // use strong type
};

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

export type AIItem = {
  client: { id: ID; name?: string; email?: string; churn_score: number };
  recommendations: AISuggestion[];
};

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

  return data;
}
