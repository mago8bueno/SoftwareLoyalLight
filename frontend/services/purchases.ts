// frontend/services/purchases.ts
import { fetcher } from './fetcher';

export type Purchase = {
  id: number;
  client_id: number;
  item_id: number;
  quantity: number;
  total_price?: number;
  created_at?: string;
};

// ---- LISTAR ----
export async function listPurchases(): Promise<Purchase[]> {
  const { data } = await fetcher.get<Purchase[]>('/purchases/');
  return data ?? [];
}

// ---- CREAR ----
export async function createPurchase(payload: {
  client_id: number;
  item_id: number;
  quantity: number;
}): Promise<Purchase> {
  const { data } = await fetcher.post<Purchase>('/purchases/', payload);
  return data;
}
