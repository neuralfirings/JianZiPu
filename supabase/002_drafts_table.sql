-- Testers' drafts as table rows instead of drafts/<user id>/draft.json files. Run once in the SQL
-- editor after 001_setup.sql. Safe to run again.
--
-- What it makes:
--   drafts            one row per person: their draft bundle (app/src/lib/bundle.ts) as JSON
--   save_draft(...)   writes your own row only if nobody saved it since you loaded it
--
-- Then copy the old files across (builder/scripts/migrate_drafts.py), check the rows, and run
-- 003_drop_drafts_bucket.sql (builder/README.md "Hosted pilot").

create table if not exists public.drafts (
  user_id uuid primary key references auth.users (id) on delete cascade,
  bundle jsonb not null,
  base_commit text,
  version integer not null default 1,
  updated_at timestamptz not null default now()
);
alter table public.drafts enable row level security;

drop policy if exists "drafts: read own" on public.drafts;
create policy "drafts: read own" on public.drafts for select to authenticated
  using (user_id = auth.uid());
drop policy if exists "drafts: admins read all" on public.drafts;
create policy "drafts: admins read all" on public.drafts for select to authenticated
  using (public.is_admin());
drop policy if exists "drafts: add own" on public.drafts;
create policy "drafts: add own" on public.drafts for insert to authenticated
  with check (user_id = auth.uid());
drop policy if exists "drafts: change own" on public.drafts;
create policy "drafts: change own" on public.drafts for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "drafts: delete own" on public.drafts;
create policy "drafts: delete own" on public.drafts for delete to authenticated
  using (user_id = auth.uid());

-- Save the caller's draft in one step. p_expected is the updated_at the app loaded (null: it saw no
-- draft). Returns the new updated_at, or raises 'conflict' when the row changed (or appeared)
-- since: another tab or computer saved, and the app asks which version stays.
-- security invoker: it runs under the row rules above, so it can only ever touch your own row.
create or replace function public.save_draft(p_bundle jsonb, p_expected timestamptz)
  returns timestamptz language plpgsql security invoker set search_path = public as $$
declare
  stamp timestamptz;
begin
  if auth.uid() is null then
    raise exception 'not signed in';
  end if;
  if p_expected is null then
    insert into public.drafts (user_id, bundle, base_commit)
    values (auth.uid(), p_bundle, p_bundle #>> '{manifest,base,commit}')
    on conflict (user_id) do nothing
    returning updated_at into stamp;
  else
    update public.drafts
       set bundle = p_bundle, base_commit = p_bundle #>> '{manifest,base,commit}',
           version = version + 1, updated_at = clock_timestamp()
     where user_id = auth.uid() and updated_at = p_expected
    returning updated_at into stamp;
  end if;
  if stamp is null then
    raise exception 'conflict' using errcode = 'P0001', hint = 'draft saved elsewhere';
  end if;
  return stamp;
end;
$$;
revoke all on function public.save_draft(jsonb, timestamptz) from public, anon;
grant execute on function public.save_draft(jsonb, timestamptz) to authenticated;
