create table if not exists public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text,
  phone text,
  created_at timestamp with time zone default now()
);

-- desactiva RLS mientras desarrollas
alter table public.clients disable row level security;
