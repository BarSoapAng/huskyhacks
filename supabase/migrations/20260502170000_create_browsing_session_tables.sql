create extension if not exists "pgcrypto";

create table if not exists public.bad_domains (
  id uuid primary key default gen_random_uuid(),
  url text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.visits (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  duration double precision not null default 0,
  url text not null,
  normalized_url text not null,
  domain text not null default '',
  page_title text not null default '',
  last_seen_at timestamptz not null default now()
);

alter table public.visits
  add column if not exists id uuid default gen_random_uuid(),
  add column if not exists user_id uuid references auth.users(id) on delete cascade,
  add column if not exists "timestamp" timestamptz not null default now(),
  add column if not exists duration double precision not null default 0,
  add column if not exists url text not null default '',
  add column if not exists normalized_url text not null default '',
  add column if not exists domain text not null default '',
  add column if not exists page_title text not null default '',
  add column if not exists last_seen_at timestamptz not null default now();

create index if not exists visits_user_last_seen_idx
  on public.visits (user_id, last_seen_at desc);

create index if not exists visits_user_normalized_url_idx
  on public.visits (user_id, normalized_url);

create table if not exists public.procrastination_session (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  active boolean not null default true,
  duration double precision not null default 0,
  visits uuid[] not null default '{}'
);

alter table public.procrastination_session
  add column if not exists id uuid default gen_random_uuid(),
  add column if not exists user_id uuid references auth.users(id) on delete cascade,
  add column if not exists "timestamp" timestamptz not null default now(),
  add column if not exists active boolean not null default true,
  add column if not exists duration double precision not null default 0,
  add column if not exists visits uuid[] not null default '{}';

create index if not exists procrastination_session_user_active_idx
  on public.procrastination_session (user_id, active, "timestamp" desc);

create table if not exists public.productive_session (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  active boolean not null default true,
  duration double precision not null default 0,
  visits uuid[] not null default '{}'
);

alter table public.productive_session
  add column if not exists id uuid default gen_random_uuid(),
  add column if not exists user_id uuid references auth.users(id) on delete cascade,
  add column if not exists "timestamp" timestamptz not null default now(),
  add column if not exists active boolean not null default true,
  add column if not exists duration double precision not null default 0,
  add column if not exists visits uuid[] not null default '{}';

create index if not exists productive_session_user_active_idx
  on public.productive_session (user_id, active, "timestamp" desc);

create table if not exists public.allowed_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  "timestamp" timestamptz not null default now(),
  active boolean not null default true,
  duration double precision not null default 0,
  visits uuid[] not null default '{}'
);

alter table public.allowed_sessions
  add column if not exists id uuid default gen_random_uuid(),
  add column if not exists user_id uuid references auth.users(id) on delete cascade,
  add column if not exists "timestamp" timestamptz not null default now(),
  add column if not exists active boolean not null default true,
  add column if not exists duration double precision not null default 0,
  add column if not exists visits uuid[] not null default '{}';

create index if not exists allowed_sessions_user_active_idx
  on public.allowed_sessions (user_id, active, "timestamp" desc);

alter table public.bad_domains enable row level security;
alter table public.visits enable row level security;
alter table public.procrastination_session enable row level security;
alter table public.productive_session enable row level security;
alter table public.allowed_sessions enable row level security;

drop policy if exists "Authenticated users can read bad domains" on public.bad_domains;
create policy "Authenticated users can read bad domains"
  on public.bad_domains
  for select
  to authenticated
  using (true);

drop policy if exists "Users can manage own visits" on public.visits;
create policy "Users can manage own visits"
  on public.visits
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can manage own procrastination sessions" on public.procrastination_session;
create policy "Users can manage own procrastination sessions"
  on public.procrastination_session
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can manage own productive sessions" on public.productive_session;
create policy "Users can manage own productive sessions"
  on public.productive_session
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can manage own allowed sessions" on public.allowed_sessions;
create policy "Users can manage own allowed sessions"
  on public.allowed_sessions
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

insert into public.bad_domains (url)
values
  ('youtube.com/shorts'),
  ('instagram.com/reels'),
  ('instagram.com/explore'),
  ('tiktok.com'),
  ('reddit.com/r/all'),
  ('reddit.com/r/popular')
on conflict (url) do nothing;
