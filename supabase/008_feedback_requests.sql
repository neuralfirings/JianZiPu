-- Requests and comments from the font page (after 007_feedback_kind.sql; safe to run again):
--   request  a character the font doesn't have yet ("Request a character"); its 中文, pinyin and
--            where it was seen are in `details`, the message says what it means or how it's played
--   comment  a note on a coming character, named by its id in `upcoming_id` (u12), with its name as
--            the page showed it in details.about
-- Run it before deploying the feedback function that sends them; one deployed before keeps each
-- request as feedback on the page, with its details written into the message.

alter table public.feedback add column if not exists upcoming_id text;
alter table public.feedback add column if not exists details jsonb;

alter table public.feedback drop constraint if exists feedback_kind_check;
alter table public.feedback add constraint feedback_kind_check
  check (kind in ('row', 'page', 'contact', 'request', 'comment'));

create index if not exists feedback_upcoming_idx on public.feedback (upcoming_id, created_at desc) where upcoming_id is not null;
