# Feedback from the font page

A Supabase Edge Function that takes the font page's feedback form
(jianzipufont.com: the feedback button on each glossary row, Feedback in the sticky
bar, "Request it" and "tell me" under a search that finds nothing, Request a character
in the glossary's intro, and "Send feedback" at the foot of the page). Each message is kept in `public.feedback`
(`supabase/006_feedback.sql`) with its pictures in the private `feedback`
bucket, and emailed to every admin (`profiles.role = 'admin'`) through
[Resend](https://resend.com), pictures attached, replying to the sender when
they left an email.

Its `GET` is the font page's list of coming characters (the glossary's ghost rows,
`supabase/009_upcoming.sql`): only the rows at stage planned, draft or test with a
section, and only what the page shows (never who asked or what they wrote), each
drawing as its public address and, at stage test, the candidate's font. Any page
may read it; it's kept for a minute.

| File | What it does |
| --- | --- |
| `check.ts` | What the form may send: fields and lengths, up to 5 pictures (8 MB each, 25 MB together), the spam trap, which pages may post |
| `mail.ts` | The admins' email (the Change Request emails' look, `../notify/templates.ts`) |
| `index.ts` | Stores the pictures and the message, then sends the email; at most 5 messages an hour from one network address; checks Cloudflare Turnstile when `TURNSTILE_SECRET` is set; `GET` lists the coming characters |
| `ghosts.ts` | What the `GET` gives the page for each row of `upcoming` |

## Setting it up

1. **The table and bucket**: run `supabase/006_feedback.sql`, then `supabase/007_feedback_kind.sql`,
   `supabase/008_feedback_requests.sql` and `supabase/009_upcoming.sql` (coming characters), in the SQL editor. In the Builder's project 006 also lets its admins read the table from a
   signed-in app. 007 adds `kind`, 008 the kinds `request` and `comment` with `upcoming_id` and
   `details`: run them before deploying a function that sends them (one deployed first still
   saves every message, a request as feedback on the page with its details in the message, and
   logs which migration is missing).
2. **Secrets**: it uses the Change Request emails' `RESEND_API_KEY` and `MAIL_FROM`
   (`../notify/README.md`), so nothing new is needed. Optional:

   ```bash
   supabase secrets set FEEDBACK_SALT=<a long random string> \
     FEEDBACK_FROM="JianZiPu font <font@jianzipufont.com>"
   ```

   `FEEDBACK_SALT` keeps the hourly limit's hashes of senders' addresses from being
   guessed; `FEEDBACK_TO` (comma-separated) sends the emails there instead of to the
   Builder's admins (needed in a project without them); `FEEDBACK_FROM` sends from
   another address than `MAIL_FROM`;
   `FEEDBACK_ORIGINS` (comma-separated) lets other pages post, beyond
   jianzipufont.com, its Cloudflare previews (`*.jianzipu.pages.dev`), the Builder's
   copy of the page (builder.jianzipufont.com/site, Railway previews
   `jzpbuilder-*.up.railway.app`, `jianzipu-*.up.railway.app`) and your own computer.
   `TURNSTILE_SECRET` turns on the spam check (Cloudflare Turnstile, the page's
   `window.TURNSTILE_SITEKEY`; `docs/maintainers/setup.md` says how): a check that
   was sent must pass. `TURNSTILE_REQUIRED` = `1` also refuses messages without one;
   set it once the live page has the site key.
3. **Deploy**: `supabase functions deploy feedback --no-verify-jwt` (visitors aren't
   signed in; `check.ts` decides what gets in). Or in the dashboard, without the CLI:
   - Make one file of it (the dashboard's editor can't reach `../notify/`):
     `deno bundle supabase/functions/feedback/index.ts -o feedback-index.ts`.
   - Edge Functions → Deploy a new function → Via Editor. Name it `feedback`, paste
     the file over `index.ts`, and deploy.
   - In the function's settings, turn off **Enforce JWT verification** and save.
     Left on, every message is refused before the function sees it.
   - Edge Functions → Secrets: check `RESEND_API_KEY` and `MAIL_FROM` are there
     (the Change Request emails set them), and add `FEEDBACK_SALT`.
4. **The page**: set `window.FEEDBACK_URL` near the top of `site/index.html` to
   `https://<project>.supabase.co/functions/v1/feedback`. Until it's set, the page
   shows no feedback buttons or links.

## Reading and answering

Each message arrives as an email: reply to it to answer the sender. All of them are
in Dashboard → Table Editor → `feedback`, newest first by `created_at`. Set
`status` from its drop-down:

| status | Meaning |
| --- | --- |
| `new` | Not looked at (every message starts here) |
| `read` | Seen |
| `wip` | Taken on. A request set to `wip` gets its row in `upcoming`, and the font page shows it as Planned once you set its `section` |
| `ticket` | Made into a ticket: put its link in `ticket` |
| `wont_do` | Not changing it |
| `need_info` | Asked the sender for more |
| `done` | Its character is released: write to them |

`kind` says what it is: `row` (the button on a glossary row), `page` (Feedback in the
sticky bar, "tell me", Send feedback), `contact` (Contact me, which asks for an email
and sends "Message from …" instead of "Feedback on …"), `request` (Request a character,
in the glossary's intro and under a search that finds nothing: `details` holds its
`zh`, `pinyin` and where it was `seen`, the message what it means; the email says
"Request: 不动 (bù dòng)") or `comment` (on a coming character, `upcoming_id` naming
it, e.g. `u12`, and `details.about` its name as the page showed it; needs an email, as a request does). `note` is yours, for anything else. The pictures are in Storage → `feedback`, one
folder per message (the message's `id`); `pictures` lists their paths.

## Changing it

```bash
deno test supabase/functions/feedback
supabase functions deploy feedback --no-verify-jwt
```
