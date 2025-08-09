// frontend/services/clients.ts
import { fetcher } from './fetcher';

export type Client = {
  id: number | string;
  name: string;
  email?: string | null;
  phone?: string | null;
  churn_score?: number | null;
};

export type ClientCreate = {
  name: string;
  email?: string;
  phone?: string;
};

/**
 * Lista completa de clientes. Acepta búsqueda opcional (?q=...).
 * Si el backend no soporta el filtro, simplemente lo ignorará.
 */
export async function getClients(search?: string): Promise<Client[]> {
  const params = search ? { q: search } : undefined;
  const { data } = await fetcher.get<Client[]>('/clients/', { params });
  return data ?? [];
}

/**
 * Versión light para selects: solo id y name.
 * (La usa purchases.tsx)
 */
export async function listClients(): Promise<Pick<Client, 'id' | 'name'>[]> {
  const rows = await getClients();
  return rows.map((c) => ({
    id: Number(c.id),
    name: c.name ?? `Cliente ${c.id}`,
  }));
}

/** Crear cliente */
export async function createClient(body: ClientCreate): Promise<Client> {
  const { data } = await fetcher.post<Client>('/clients/', body);
  return data;
}

/** Actualizar cliente (patch parcial) */
export async function updateClient(id: number, data: Partial<ClientCreate>): Promise<Client> {
  const res = await fetcher.patch<Client>(`/clients/${id}/`, data); // <- barra final
  return res.data;
}

/** Borrar cliente */
export async function deleteClient(id: number): Promise<void> {
  await fetcher.delete(`/clients/${id}/`); // <- barra final
}
