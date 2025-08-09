export interface Client {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  churnRate?: number;
  created_at?: string;
}

export interface ClientCreate {
  name: string;
  email?: string;
  phone?: string;
}

export interface Item {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  created_at?: string;
}

export interface Purchase {
  id: string;
  client_id: string;
  item_id: string;
  quantity: number;
  total_price: number;
  purchased_at?: string;
}
