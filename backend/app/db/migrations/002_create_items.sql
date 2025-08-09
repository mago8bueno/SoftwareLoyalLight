create table if not exists public.items (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  price numeric(10,2) not null,
  image_url text,
  created_at timestamp with time zone default now()
);

alter table public.items disable row level security;
