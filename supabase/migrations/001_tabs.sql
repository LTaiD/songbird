-- Songbird tabs (spec Phase 8): editable tab JSON only — no PDFs, no recordings.
-- Run in the Supabase SQL editor (or `supabase db push`).

create table if not exists public.tabs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'untitled tab',
  tab_json jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tabs_user_idx on public.tabs (user_id, updated_at desc);

-- Row Level Security: a user can CRUD only their own rows.
alter table public.tabs enable row level security;

create policy "own tabs select" on public.tabs
  for select using (auth.uid() = user_id);
create policy "own tabs insert" on public.tabs
  for insert with check (auth.uid() = user_id);
create policy "own tabs update" on public.tabs
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own tabs delete" on public.tabs
  for delete using (auth.uid() = user_id);
