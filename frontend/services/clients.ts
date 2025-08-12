// frontend/services/clients.ts
import { fetcher } from "./fetcher";

export type Client = {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  churn_score?: number | null;
  owner_id?: string;
};

export type ClientCreate = {
  name: string;
  email?: string;
  phone?: string;
};

function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export async function getClients(search?: string): Promise<Client[]> {
  const params = search ? { q: search } : undefined;
  const { data } = await fetcher.get<Client[]>("/clients/", { params });
  return data ?? [];
}

export async function listClients(): Promise<Pick<Client, "id" | "name">[]> {
  const rows = await getClients();
  return rows.map((c) => ({ id: c.id, name: c.name ?? `Cliente ${c.id}` }));
}

export async function createClient(body: ClientCreate): Promise<Client> {
  if (body.email && !isValidEmail(body.email)) {
    throw new Error("Email inválido");
  }
  const { data } = await fetcher.post<Client>("/clients/", body);
  return data;
}

export async function updateClient(id: string, data: Partial<ClientCreate>): Promise<Client> {
  if (data.email && !isValidEmail(data.email)) {
    throw new Error("Email inválido");
  }
  const res = await fetcher.put<Client>(`/clients/${id}`, data);
  return res.data;
}

export async function deleteClient(id: string): Promise<void> {
  await fetcher.delete(`/clients/${id}`);
}
