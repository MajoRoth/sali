-- sali — Supabase schema for saved receipts.
-- Run in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).

create table if not exists public.receipts (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  name       text not null,
  items      jsonb not null default '[]'::jsonb,
  -- The full extracted Receipt Document. `items` is the flattened view the
  -- list screen renders; this is everything the extractor read, and it is what
  -- lets a saved receipt be re-priced later against wherever the shopper is
  -- standing then. Nullable because receipts saved before this column existed
  -- have no document, and the app degrades to `items` when it is absent.
  document   jsonb,
  created_at timestamptz not null default now()
);

-- Safe to re-run on a project created before `document` existed.
alter table public.receipts add column if not exists document jsonb;

create index if not exists receipts_user_created_idx
  on public.receipts (user_id, created_at desc);

-- Row Level Security: every user sees and writes only their own receipts.
-- Without this, the anon key would expose every row to every visitor.
alter table public.receipts enable row level security;

drop policy if exists "receipts are private to their owner" on public.receipts;
create policy "receipts are private to their owner"
  on public.receipts
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
