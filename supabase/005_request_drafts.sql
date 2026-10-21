-- A Change Request not sent yet: the Send form's title, notes, credit and ticked changes, kept on
-- the tester's own drafts row so it follows them to another computer. Run once in the SQL editor
-- after 004_change_requests.sql. Safe to run again.
--
-- Shape (app/src/lib/requests.ts RequestDraft):
--   {"title", "notes", "credit", "chosen": [item ids], "seen": [item ids shown when saved], "saved_at"}
-- The row rules of 002 already cover it: each person reads and changes only their own row. Saving
-- it doesn't touch updated_at, so it never looks like the draft was saved somewhere else.

alter table public.drafts add column if not exists request_draft jsonb;
