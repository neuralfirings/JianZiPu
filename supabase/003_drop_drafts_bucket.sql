-- Retire the old drafts bucket once builder/scripts/migrate_drafts.py has copied every
-- drafts/<user id>/draft.json into public.drafts (002_drafts_table.sql) and you have checked the
-- rows (Table Editor → drafts). Run once in the SQL editor. Safe to run again.
--
-- Afterwards delete the bucket itself: Storage → drafts → Delete bucket (it has to be emptied first;
-- the dashboard offers that). The assets bucket stays: it holds the TW-Kai base font.

drop policy if exists "drafts: read own" on storage.objects;
drop policy if exists "drafts: add own" on storage.objects;
drop policy if exists "drafts: change own" on storage.objects;
drop policy if exists "drafts: delete own" on storage.objects;
drop policy if exists "drafts: admins read all" on storage.objects;
