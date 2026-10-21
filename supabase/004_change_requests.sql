-- Change Requests: a tester sends chosen changes from their draft, with a title, notes and how
-- they'd like to be credited; an admin keeps or skips each change, replies, and takes the kept ones
-- into a release. Run once in the SQL editor after 002_drafts_table.sql. Safe to run again.
--
-- What it makes:
--   profiles.credit                 how a tester likes to be credited (prefills the Send form)
--   set_my_credit(text)             the only way to change it (so nobody can change their own role)
--   change_requests                 one row per Change Request
--   withdraw_change_request(uuid)   the author takes a request back, until an admin keeps a change
--
-- Emails (new request, withdrawn, status changes): supabase/functions/notify (see its README).
--
-- Status: sent → in_review → in_candidate → released, or declined / withdrawn.
-- decisions: {"<item id>": "keep" | "skip"} (item ids from app/src/lib/merge.ts).

-- ---------------------------------------------------------------- credit

alter table public.profiles add column if not exists credit text;

create or replace function public.set_my_credit(p_credit text) returns void
  language sql security definer set search_path = public as $$
  update public.profiles set credit = nullif(left(trim(p_credit), 200), '') where id = auth.uid();
$$;
revoke all on function public.set_my_credit(text) from public, anon;
grant execute on function public.set_my_credit(text) to authenticated;

-- ---------------------------------------------------------------- change requests

create table if not exists public.change_requests (
  id uuid primary key default gen_random_uuid(),
  author uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title text not null check (length(trim(title)) between 1 and 200),
  notes text not null default '' check (length(notes) <= 20000),
  credit text not null default '' check (length(credit) <= 200),
  bundle jsonb not null,
  item_ids text[] not null check (cardinality(item_ids) > 0),
  base_commit text,
  status text not null default 'sent'
    check (status in ('sent', 'in_review', 'in_candidate', 'released', 'declined', 'withdrawn')),
  decisions jsonb not null default '{}'::jsonb,
  reply text not null default '' check (length(reply) <= 20000),
  release text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  reviewed_at timestamptz,
  released_at timestamptz
);
create index if not exists change_requests_author on public.change_requests (author, created_at desc);
alter table public.change_requests enable row level security;

create or replace function public.touch_updated_at() returns trigger
  language plpgsql set search_path = public as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
drop trigger if exists change_requests_touch on public.change_requests;
create trigger change_requests_touch before update on public.change_requests
  for each row execute function public.touch_updated_at();

drop policy if exists "requests: read own" on public.change_requests;
create policy "requests: read own" on public.change_requests for select to authenticated
  using (author = auth.uid());
drop policy if exists "requests: admins read all" on public.change_requests;
create policy "requests: admins read all" on public.change_requests for select to authenticated
  using (public.is_admin());
-- a tester sends their own, as a fresh request: no decisions, reply or release of their own making
drop policy if exists "requests: send own" on public.change_requests;
create policy "requests: send own" on public.change_requests for insert to authenticated
  with check (author = auth.uid() and status = 'sent' and decisions = '{}'::jsonb and reply = ''
              and release is null and reviewed_at is null and released_at is null);
-- only admins change a request (decisions, reply, status, release); authors withdraw below
drop policy if exists "requests: admins update" on public.change_requests;
create policy "requests: admins update" on public.change_requests for update to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- The author takes a request back while nothing in it has been kept yet. Returns true if it was
-- withdrawn, false if it can no longer be (an admin kept a change, or it is already finished).
create or replace function public.withdraw_change_request(p_id uuid) returns boolean
  language plpgsql security definer set search_path = public as $$
declare
  n integer;
begin
  update public.change_requests
     set status = 'withdrawn'
   where id = p_id and author = auth.uid()
     and (status = 'sent'
          or (status = 'in_review' and not exists (select 1 from jsonb_each_text(decisions) d where d.value = 'keep')));
  get diagnostics n = row_count;
  return n > 0;
end;
$$;
revoke all on function public.withdraw_change_request(uuid) from public, anon;
grant execute on function public.withdraw_change_request(uuid) to authenticated;
