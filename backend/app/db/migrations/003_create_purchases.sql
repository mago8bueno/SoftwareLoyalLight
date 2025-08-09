create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references public.clients(id) on delete cascade,
  item_id uuid not null references public.items(id) on delete restrict,
  quantity integer not null check (quantity > 0),
  total numeric(10,2) generated always as (quantity *  (select price from public.items where items.id = purchases.item_id)) stored,
  purchased_at timestamp with time zone default now()
);

alter table public.purchases disable row level security;
