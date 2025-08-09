// services/items.ts
import { fetcher } from './fetcher';

export type Item = {
  id: number;
  name: string;
  price: number;
  stock: number;
  image_url?: string | null;
};

// ---- LISTAR (con búsqueda opcional) ----
// Todas las rutas terminan en "/" para evitar 307 + CORS
export async function listItems(search?: string): Promise<Item[]> {
  const { data } = await fetcher.get<Item[]>('/items/', {
    params: search ? { q: search } : undefined,
  });
  return data;
}

// ---- CREAR ----
export async function createItem(
  payload: Omit<Item, 'id'> & { image_url?: string | null },
): Promise<Item> {
  const { data } = await fetcher.post<Item>('/items/', payload);
  return data;
}

// ---- ELIMINAR ----
export async function deleteItem(id: number | string): Promise<void> {
  await fetcher.delete(`/items/${id}/`); // <- barra final
}

// ---- SUBIR IMAGEN ----
// Requiere endpoint backend POST /items/upload-image/
export async function uploadItemImage(
  file: File,
  filename?: string,
): Promise<{ image_url: string }> {
  const form = new FormData();
  form.append('file', file, filename ?? file.name);

  const { data } = await fetcher.post<{ image_url: string }>('/items/upload-image/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}
