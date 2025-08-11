// services/items.ts
import { fetcher } from "./fetcher";

export type Item = {
  id: string; // IDs devueltos por Supabase son UUID
  name: string;
  price: number;
  stock: number;
  image_url?: string | null;
};

export async function listItems(search?: string): Promise<Item[]> {
  const { data } = await fetcher.get<Item[]>("/items/", {
    params: search ? { q: search } : undefined,
  });
  return data;
}

export async function createItem(
  payload: Omit<Item, "id"> & { image_url?: string | null },
): Promise<Item> {
  const { data } = await fetcher.post<Item>("/items/", payload);
  return data;
}

// ⬇️ FIX: sin barra final
export async function deleteItem(id: string): Promise<void> {
  await fetcher.delete(`/items/${id}`);
}

export async function uploadItemImage(
  file: File,
  filename?: string,
): Promise<{ image_url: string }> {
  const form = new FormData();
  form.append("file", file, filename ?? file.name);

  const { data } = await fetcher.post<{ image_url: string }>(
    "/items/upload-image/",
    form,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return data;
}
