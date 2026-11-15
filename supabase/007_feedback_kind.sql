-- What each piece of feedback is (after 006_feedback.sql; safe to run again):
--   row      about a glossary row (the button on the row)
--   page     about the page (Feedback in the sticky bar, "Tell me" under a search that found nothing,
--            Send feedback at the foot)
--   contact  a note to you (Contact me)
-- Run it before deploying the feedback function that sends it; one deployed before keeps saving
-- messages without it.

alter table public.feedback add column if not exists kind text not null default 'page';
update public.feedback set kind = 'row' where glossary_row is not null and kind = 'page';
do $$ begin
  alter table public.feedback add constraint feedback_kind_check check (kind in ('row', 'page', 'contact'));
exception when duplicate_object then null;
end $$;
create index if not exists feedback_kind_idx on public.feedback (kind, created_at desc);
