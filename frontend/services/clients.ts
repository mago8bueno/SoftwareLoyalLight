// frontend/services/clients.ts  
import { fetcher } from "./fetcher";  
  
export type Client = {  
  id: string; // ← CORREGIDO: usar solo string para consistencia  
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
  
// ← AÑADIR: Validación de email  
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
  // ← CORREGIDO: mantener id como string  
  return rows.map((c) => ({ id: c.id, name: c.name ?? `Cliente ${c.id}` }));  
}  
  
// ← CORREGIDO: Añadir validación de email  
export async function createClient(body: ClientCreate): Promise<Client> {  
  // Validar email si se proporciona  
  if (body.email && !isValidEmail(body.email)) {  
    throw new Error("Email inválido");  
  }  
    
  const { data } = await fetcher.post<Client>("/clients/", body);  
  return data;  
}  
  
// ← CORREGIDO: usar string para id  
export async function updateClient(id: string, data: Partial<ClientCreate>): Promise<Client> {  
  // Validar email si se proporciona  
  if (data.email && !isValidEmail(data.email)) {  
    throw new Error("Email inválido");  
  }  
    
  const res = await fetcher.put<Client>(`/clients/${id}`, data);  
  return res.data;  
}  
  
// ← CORREGIDO: eliminar duplicado y usar string para id  
export async function deleteClient(id: string): Promise<void> {  
  await fetcher.delete(`/clients/${id}`);  
}
