-- Supabase setup for the hosted Builder pilot. Run once in the SQL editor of the project
-- (Dashboard → SQL → New query → paste → Run). Safe to run again.
--
-- What it makes:
--   profiles        one row per invited person (name, email, role 'tester' | 'admin')
--   bucket assets   private; only the server's service key reads it (the TW-Kai base font)
-- Then run 002_drafts_table.sql (testers' drafts), 004_change_requests.sql (Change Requests) and
-- 005_request_drafts.sql (a Change Request saved before sending).
--
-- After running it (docs: builder/README.md "Hosted pilot"):
--   Authentication → Sign In / Providers → Email: turn OFF "Allow new users to sign up"
--   Authentication → URL Configuration: Site URL = the pilot's address; Redirect URLs add
--     https://<pilot domain>/** and http://127.0.0.1:5713/** (your local Builder's Review sign-in)
--   Authentication → Emails: paste the subjects and HTML from supabase/emails/ (see its README)
--   Authentication → Users → Invite user: each tester (and yourself)
--   update public.profiles set role = 'admin', name = 'Nancy' where email = '<your email>';
--   Storage → assets: upload TW-Kai-98.ttf

-- ---------------------------------------------------------------- people

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  name text,
  role text not null default 'tester' check (role in ('tester', 'admin')),
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;

-- security definer: reads profiles without going through its own row rules (no recursion)
create or replace function public.is_admin() returns boolean
  language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$;

drop policy if exists "read own profile" on public.profiles;
create policy "read own profile" on public.profiles for select to authenticated
  using (id = auth.uid());
drop policy if exists "admins read all profiles" on public.profiles;
create policy "admins read all profiles" on public.profiles for select to authenticated
  using (public.is_admin());
-- no insert/update/delete policies: rows come from the trigger, roles and names from the SQL editor

-- an invited user gets a profile row
create or replace function public.handle_new_user() returns trigger
  language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'))
  on conflict (id) do nothing;
  return new;
end;
$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- people invited before this script ran
insert into public.profiles (id, email)
select id, email from auth.users
on conflict (id) do nothing;

-- ---------------------------------------------------------------- storage

insert into storage.buckets (id, name, public)
values ('assets', 'assets', false)
on conflict (id) do update set public = false;
-- assets has no policies on purpose: only the service key (the server) can read it
