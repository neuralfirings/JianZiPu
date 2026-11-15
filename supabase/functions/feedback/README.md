# Feedback from the font page

A Supabase Edge Function that takes the font page's feedback form
(jianzipufont.com: the feedback button on each glossary row, Feedback in the sticky
bar, "Tell me" under a search that finds nothing, and "Send feedback" at the foot
of the page). Each message is kept in `public.feedback`
(`supabase/006_feedback.sql`) with its pictures in the private `feedback`
bucket, and emailed to every admin (`profiles.role = 'admin'`) through
[Resend](https://resend.com), pictures attached, replying to the sender when
they left an email.

| File | What it does |
| --- | --- |
| `check.ts` | What the form may send: fields and lengths, up to 5 pictures (8 MB each, 25 MB together), the spam trap, which pages may post |
| `mail.ts` | The admins' email (the Change Request emails' look, `../notify/templates.ts`) |
| `index.ts` | Stores the pictures and the message, then sends the email; at most 5 messages an hour from one network address |

## Setting it up

1. **The table and bucket**: run `supabase/006_feedback.sql` in the SQL editor. In the
   Builder's project it also lets its admins read the table from a signed-in app.
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
   `jianzipu-*.up.railway.app`) and your own computer.
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
| `ticket` | Made into a ticket: put its link in `ticket` |
| `wont_do` | Not changing it |
| `need_info` | Asked the sender for more |

`note` is yours, for anything else. The pictures are in Storage → `feedback`, one
folder per message (the message's `id`); `pictures` lists their paths.

## Changing it

```bash
deno test supabase/functions/feedback
supabase functions deploy feedback --no-verify-jwt
```
