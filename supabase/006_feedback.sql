-- Feedback from the font page (jianzipufont.com): the feedback button on each glossary row, Feedback in
-- the sticky bar, "Tell me" under a search that finds nothing, and "Send feedback" at the foot of the page. Run once in the SQL editor; safe to run again. It stands
-- on its own: in the Builder's project (after 001) admins may also read and set statuses from a
-- signed-in app; in any other project only the dashboard and the function (service key) reach it.
--
-- What it makes:
--   feedback          one row per message: what it's about, the message, who sent it (if they said),
--                     its pictures, and a status you set: new → read → ticket / wont_do / need_info
--   bucket feedback   private; the pictures, one folder per message (<id>/picture-1.jpg)
--
-- Messages come in only through the Edge Function supabase/functions/feedback (its README), which
-- uses the service key: there is no insert policy, so nobody can write here from a browser.
-- Change a message's status in Dashboard → Table Editor → feedback (status is a drop-down).

do $$ begin
  create type public.feedback_status as enum ('new', 'read', 'ticket', 'wont_do', 'need_info');
exception when duplicate_object then null;
end $$;
comment on type public.feedback_status is
  'new: not looked at; read: seen; ticket: made into a ticket (link in ticket); wont_do: not changing it; need_info: asked the sender for more';

create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  status public.feedback_status not null default 'new',
  -- what it's about: the glossary row as the page showed it, "2 · 中 · d · zhōng (1.1. Which Finger to Use)";
  -- empty for feedback on the page as a whole
  glossary_row text,
  link text,                                   -- the row on the page (…/#2), or the page
  message text not null,
  name text,
  email text,                                  -- to reply to; never shown anywhere
  pictures text[] not null default '{}',       -- paths in the feedback bucket
  ticket text,                                 -- the ticket it became (a link), when status is ticket
  note text,                                   -- your own note on it
  sender text                                  -- a hash of the sender's network address, for the hourly limit; not the address
);
create index if not exists feedback_status_idx on public.feedback (status, created_at desc);
create index if not exists feedback_sender_idx on public.feedback (sender, created_at desc);
alter table public.feedback enable row level security;

-- the Builder's admins (001_setup.sql's is_admin()), where this project has them; with no policy at
-- all, the table is the dashboard's and the function's alone
do $$ begin
  if to_regprocedure('public.is_admin()') is not null then
    execute 'drop policy if exists "feedback: admins read" on public.feedback';
    execute 'create policy "feedback: admins read" on public.feedback for select to authenticated using (public.is_admin())';
    execute 'drop policy if exists "feedback: admins update" on public.feedback';
    execute 'create policy "feedback: admins update" on public.feedback for update to authenticated using (public.is_admin()) with check (public.is_admin())';
    execute 'drop policy if exists "feedback: admins delete" on public.feedback';
    execute 'create policy "feedback: admins delete" on public.feedback for delete to authenticated using (public.is_admin())';
  end if;
end $$;

create or replace function public.feedback_touch() returns trigger
  language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;
drop trigger if exists feedback_touch on public.feedback;
create trigger feedback_touch before update on public.feedback
  for each row execute function public.feedback_touch();

-- ---------------------------------------------------------------- pictures

insert into storage.buckets (id, name, public)
values ('feedback', 'feedback', false)
on conflict (id) do update set public = false;
-- the function writes with the service key; the dashboard shows them; the Builder's admins may read
-- them too, where this project has them
do $$ begin
  if to_regprocedure('public.is_admin()') is not null then
    execute 'drop policy if exists "feedback pictures: admins read" on storage.objects';
    execute 'create policy "feedback pictures: admins read" on storage.objects for select to authenticated using (bucket_id = ''feedback'' and public.is_admin())';
  end if;
end $$;
