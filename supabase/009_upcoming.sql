-- Coming characters: the glossary's "ghost" rows (after 008_feedback_requests.sql; safe to run again).
--
-- What it makes:
--   feedback statuses wip (you've taken the request on) and done (its character is released)
--   upcoming          one row per coming character. The font page shows a row while its stage is
--                     planned, draft or test and its section is set, through the feedback
--                     function's GET (never this table directly: it has no public access)
--   a trigger         setting a request's status to wip adds its row to upcoming, filled from the
--                     request, and points the request's upcoming_id at it; a request whose
--                     upcoming_id is already set (a second request for the same character) adds none
--   bucket upcoming   public; the drawings the page shows (u12.svg), named in upcoming.drawing
--
-- Admins edit and delete rows in the Builder's Review › Glossary drafts, which shows each as the page
-- will; the Builder also writes it (Review's Publish draft to glossary, Release's candidate and publish steps).

alter type public.feedback_status add value if not exists 'wip' after 'read';
alter type public.feedback_status add value if not exists 'done';
comment on type public.feedback_status is
  'new: not looked at; read: seen; wip: taken on (a request: its coming character is in upcoming); ticket: made into a ticket (link in ticket); wont_do: not changing it; need_info: asked the sender for more; done: its character is released';

do $$ begin
  create type public.upcoming_stage as enum ('planned', 'draft', 'test', 'released');
exception when duplicate_object then null;
end $$;
comment on type public.upcoming_stage is
  'planned: taken on, not drawn (badge Planned); draft: a drawing to comment on (Draft); test: in a release candidate (In release <version>); released: in the font, no longer shown';

create sequence if not exists public.upcoming_seq;

create table if not exists public.upcoming (
  id text primary key default 'u' || nextval('public.upcoming_seq'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- what the page shows
  zh text not null default '',                 -- as the glossary shows it: 不动, or 索铃 · 索鈴
  pinyin text,
  ascii text,                                  -- the spelling, once a Change Request gives it one
  meaning text,                                -- the Definition column
  section text,                                -- the glossary subtitle's id (1e); not shown until set
  after text,                                  -- the 中文 of the row it follows; empty: the section's end
  stage public.upcoming_stage not null default 'planned',
  note text,                                   -- one public line: "Redrawn Nov 24: the hook is shorter"
  drawing text,                                -- a file in the upcoming bucket (u12.svg)
  version text,                                -- the release it's in (3.400), at stage test
  -- for you and the Builder, never shown
  glyphs text[] not null default '{}',         -- the glyphs that draw it (budong_md)
  feedback_id uuid references public.feedback (id) on delete set null,   -- the request it came from
  change_request_id uuid                       -- the Change Request whose drawing it shows
);
-- added after the table's first version: running this file again adds it
alter table public.upcoming add column if not exists example text[];   -- the example's two input lines, [中文, ASCII] (引上九, yin3shang9); its drawing is the whole word
create index if not exists upcoming_stage_idx on public.upcoming (stage);
alter table public.upcoming enable row level security;

do $$ begin
  if to_regprocedure('public.is_admin()') is not null then
    execute 'drop policy if exists "upcoming: admins read" on public.upcoming';
    execute 'create policy "upcoming: admins read" on public.upcoming for select to authenticated using (public.is_admin())';
    execute 'drop policy if exists "upcoming: admins write" on public.upcoming';
    execute 'create policy "upcoming: admins write" on public.upcoming for all to authenticated using (public.is_admin()) with check (public.is_admin())';
  end if;
end $$;

drop trigger if exists upcoming_touch on public.upcoming;
create trigger upcoming_touch before update on public.upcoming
  for each row execute function public.feedback_touch();

-- ---------------------------------------------------------------- a request set to wip

create or replace function public.feedback_take_on() returns trigger
  language plpgsql security definer set search_path = public as $$
declare
  made text;
begin
  insert into public.upcoming (zh, pinyin, meaning, feedback_id)
  values (coalesce(new.details ->> 'zh', ''), new.details ->> 'pinyin', new.message, new.id)
  returning id into made;
  new.upcoming_id := made;
  return new;
end;
$$;
drop trigger if exists feedback_take_on on public.feedback;
create trigger feedback_take_on before update of status on public.feedback
  for each row
  when (new.status::text = 'wip' and old.status::text <> 'wip' and new.kind = 'request' and new.upcoming_id is null)
  execute function public.feedback_take_on();

-- ---------------------------------------------------------------- drawings

insert into storage.buckets (id, name, public, allowed_mime_types)
values ('upcoming', 'upcoming', true, array['image/svg+xml', 'image/png'])
on conflict (id) do update set public = true, allowed_mime_types = excluded.allowed_mime_types;
-- anyone may look (it's a public bucket); only the Builder's admins write, besides the dashboard
do $$ begin
  if to_regprocedure('public.is_admin()') is not null then
    execute 'drop policy if exists "upcoming drawings: admins write" on storage.objects';
    execute 'create policy "upcoming drawings: admins write" on storage.objects for all to authenticated using (bucket_id = ''upcoming'' and public.is_admin()) with check (bucket_id = ''upcoming'' and public.is_admin())';
  end if;
end $$;
