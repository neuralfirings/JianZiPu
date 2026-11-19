# Maintainer setup

The one-time setup behind the Builder, the pilot, and releases. Each part says
where the settings live. Secrets never go in this repository.

| Part | What it does | Where |
| --- | --- | --- |
| Your computer | The local Builder: Review, releases, git | this repo, `builder/.env` |
| Supabase | Sign-in, drafts, Change Requests, the base font, emails, the font page's feedback | supabase.com dashboard, `supabase/` |
| Railway | The online Builder at builder.jianzipufont.com (Review too, for admins) | railway.com, `Dockerfile` |
| Resend | Sends the Change Request and feedback emails | resend.com, `supabase/functions/notify/`, `supabase/functions/feedback/` |
| GitHub | Code, tags, releases, the ruleset on main | repository Settings, `.github/workflows/` |
| Cloudflare Pages | The font page at jianzipufont.com | dash.cloudflare.com, `site/` |
| EmailOctopus | The "send me the font" email on the font page, and the email list shared with Guqin Tabs | emailoctopus.com, `site/index.html` |

## Your computer

1. Do the setup in `builder/README.md` "Setup":
   - Python dependencies: `cd builder && pip install -e '.[test]'`;
   - the base font, copied into `builder/src_font/TW-Kai-98.ttf` (it isn't in
     the repo);
   - the app build: `cd app && npm install && npm run build`. Build it again
     after pulling app changes, or the server serves the old app.
2. Copy `builder/.env.example` to `builder/.env` (gitignored), then fill in
   `SUPABASE_URL` and `SUPABASE_ANON_KEY`. They're in Supabase → Project
   Settings → API Keys. Review's admin sign-in needs them. Never put the
   service key in this file.
3. Git must be able to push to GitHub from this copy (your own sign-in, over
   SSH or HTTPS). The Release screen runs git as you.
4. Start it with `cd builder && python3 -m jzpbuild.webserver`, then open
   http://127.0.0.1:5713/.

## Supabase

1. **The database.** In the SQL editor, run the files in `supabase/` in order:

   | File | What it adds |
   | --- | --- |
   | `001_setup.sql` | profiles (with `role`), the private `assets` bucket, row rules |
   | `002_drafts_table.sql` | the `drafts` table and `save_draft()` |
   | `003_drop_drafts_bucket.sql` | removes the old drafts bucket's policies; only needed if the bucket ever existed |
   | `004_change_requests.sql` | Change Requests, credit, `withdraw_change_request()` |
   | `005_request_drafts.sql` | unsent Change Requests saved with a draft |
   | `006_feedback.sql` | the font page's feedback (`feedback` table with a status, private `feedback` bucket) |
   | `007_feedback_kind.sql` | each message's `kind`: a glossary row, the page, or Contact me |
   | `008_feedback_requests.sql` | two more kinds, `request` (Request a character) and `comment` (on a coming character), with `upcoming_id` and `details` |
   | `009_upcoming.sql` | coming characters (the glossary's ghost rows): the `upcoming` table, statuses `wip` and `done`, the trigger that makes a row when a request is set to `wip`, the public `upcoming` bucket |

2. **Auth**, following the comments at the top of `001_setup.sql`:
   - Turn off sign-ups.
   - Set the Site URL to the pilot domain.
   - Add redirect URLs: the pilot domain, and `http://127.0.0.1:5713/**` for
     your local Review.
3. **Emails.** Paste the templates and subjects from `supabase/emails/` (its
   README says how). Do this before inviting anyone.
4. **People.** Invite each tester and yourself (Authentication → Users →
   Invite). Make yourself admin: set `role = 'admin'` on your row in
   `profiles`.
5. **The base font.** Upload `TW-Kai-98.ttf` to the `assets` bucket. The online
   Builder downloads it at start.

Moving drafts from the old Storage bucket into the table is a one-off, done in
October 2026. The steps are in `builder/README.md`, "Moving drafts from the old
bucket".

## Railway (the online Builder)

1. Create a service from this repository. It builds the root `Dockerfile` and
   deploys `main` on every merge.
2. Set these variables:
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`;
   - `SUPABASE_SERVICE_KEY` (secret; only the server uses it, to read the base
     font).

   Railway sets `PORT` and `RAILWAY_GIT_COMMIT_SHA` itself.
3. Add the custom domain `builder.jianzipufont.com`.

The "Ask for an invite" and Feedback forms post to Formspree straight from the
app (`app/src/lib/forms.ts`), so they need no setting.

A failed deploy, or one that looks old (a build error that was fixed weeks
ago), means Railway is serving an old image. Redeploy from Railway's
Deployments tab.

## Change Request emails (Resend)

`supabase/functions/notify/README.md` has the full steps. In short:

1. Create a Resend account, add and verify the `jianzipufont.com` domain (DNS
   records), and create an API key.
2. Set the secrets with
   `supabase secrets set RESEND_API_KEY=… MAIL_FROM=… NOTIFY_WEBHOOK_SECRET=… BUILDER_URL=… REVIEW_URL=…`,
   or in the dashboard under Edge Functions → Secrets. `NOTIFY_WEBHOOK_SECRET` is
   a random string you make (`openssl rand -hex 32`); `BUILDER_URL` is
   `https://builder.jianzipufont.com`, `REVIEW_URL` `http://127.0.0.1:5713`.
3. Deploy with `supabase functions deploy notify --no-verify-jwt`. Without the
   CLI: `deno bundle supabase/functions/notify/index.ts -o notify-index.ts`, then
   Edge Functions → Deploy a new function → Via Editor, name `notify`, paste the
   file over `index.ts`, deploy, and turn off **Enforce JWT verification** in its
   settings.
4. Create a database webhook: in the dashboard's left bar, **Integrations** →
   **Database Webhooks** (enable them first if asked) → Create a new hook. Name
   it `notify_change_requests`; table `change_requests`, events Insert and
   Update, type Supabase Edge Functions, function `notify`, method POST, and the
   HTTP header `x-webhook-secret` with the same string as the secret.

To check it: https://<project>.supabase.co/functions/v1/notify should answer
`forbidden` (deployed; it wants the webhook's secret), not "Requested function
was not found". Each status change shows in Edge Functions → `notify` → Logs, and
each email in Resend's logs. An email goes only when a request's status changes,
and never for a change made before the hook existed.

The email templates are in git (`supabase/functions/notify/templates.ts`). To
change one, edit it, run `deno test supabase/functions/notify`, and deploy
again.

## Feedback from the font page

The feedback button on each glossary row on jianzipufont.com, Feedback in the
sticky bar, "Tell me" under a search that finds nothing, and "Send feedback" at
the foot of the page send a message with optional photos or a
drawing to the `feedback` Edge Function. It keeps each one in the `feedback`
table (pictures in the `feedback` bucket) and emails the admins through Resend,
pictures attached. `supabase/functions/feedback/README.md` has the full steps.
In short:

1. Run `supabase/006_feedback.sql`, `supabase/007_feedback_kind.sql`,
   `supabase/008_feedback_requests.sql` and `supabase/009_upcoming.sql`.
2. Deploy with `supabase functions deploy feedback --no-verify-jwt`. It uses the
   Change Request emails' `RESEND_API_KEY` and `MAIL_FROM`; optionally set
   `FEEDBACK_SALT` to a long random string.
3. Set `window.FEEDBACK_URL` near the top of `site/index.html` to
   `https://<project>.supabase.co/functions/v1/feedback` and merge. Until then
   the page shows no feedback buttons or links.

"Contact me" on the page opens the same form, asks for an email, and is kept
with `kind` = `contact`.

Answer a message by replying to its email. Set its status in Table Editor →
`feedback`: `new`, `read`, `wip`, `ticket` (put the ticket's link in `ticket`),
`wont_do`, `need_info` or `done`.

### Spam check (Cloudflare Turnstile)

The form runs Cloudflare Turnstile once it has a site key; until then it works
without it. The secret is shared by every copy of the page, while the site key
reaches jianzipufont.com only when its pull request merges, so it goes on in two
steps:

1. Cloudflare dashboard → Turnstile → **Add widget**. Hostnames:
   `jianzipufont.com`, `jianzipu.pages.dev` (the previews), `builder.jianzipufont.com`
   and `up.railway.app` (the Builder's copy of the page and its previews).
   Widget mode: **Managed**. It gives a site key and a secret key.
2. Supabase → Edge Functions → Secrets: add `TURNSTILE_SECRET` with the secret
   key. From then on a check that was sent must pass, but a message without one
   (the live page, before step 3 merges) still goes through.
3. Set `window.TURNSTILE_SITEKEY` near the top of `site/index.html` to the site
   key, try the form on the pull request's preview, and merge. A page on your
   own computer uses Cloudflare's test key.
4. Once jianzipufont.com has the site key (a minute after the merge), add the
   secret `TURNSTILE_REQUIRED` = `1`: a message without a passing check is
   refused from then on.

### Coming characters (the glossary's ghost rows)

A visitor's **Request a character** arrives as a `request` in `feedback`. To take
one on, set its status to `wip`: a row appears in Table Editor → `upcoming`,
filled from the request. Check its words (the meaning is the visitor's), then
set `section` (the glossary subtitle's id, such as `1e`) and `after` (the 中文 of
the row it follows; empty for the section's end). The font page shows it as
**Planned** within a minute. A second request for the same character: put the
first one's `upcoming_id` on it before setting it to `wip`.

From there the Builder moves it on: Review's **Publish draft to glossary** shows a
tester's drawing (**Draft design**), a release candidate makes it **In release**,
and publishing the release takes it off the list. Set the request to `done` then,
and write to the person who asked.

## GitHub

1. **The ruleset on main.** Settings → Rules → Rulesets → New branch ruleset,
   targeting `main`:
   - Require a pull request before merging (0 approvals is fine).
   - Require the status checks `scope`, `app`, `builder` and `emails`.
   - Add Repository admin to the bypass list, so an emergency fix can still go
     straight in.

   Rulesets are free on public repositories. This makes the
   [scope rules](releasing.md#scope-rules) hold without anyone having to
   remember them.
2. **The `font-files` label** (it exists already). An admin adds it to a code
   pull request that must change font files on purpose.
3. **Merges.** Leave "Allow merge commits" on in Settings → General → Pull
   Requests, because release pull requests need it
   ([releasing.md](releasing.md#6-merge-the-pull-request)).
4. **Actions.** `release.yml` publishes releases with the workflow's own token
   (`permissions: contents: write`). No secret is needed.

## Cloudflare Pages (jianzipufont.com)

- A Pages project connected to this repository, with production branch `main`,
  no build command, and output directory `site`.
- `site/_headers` makes browsers check `JianZiPu.ttf` and `version.json` on
  every visit (`Cache-Control: no-cache`; an unchanged file is a short "not
  modified" reply), so people get a new release as soon as it deploys. A
  release replaces the font at the same URL, so a longer cache would keep the
  old font in browsers that saw it before.

## EmailOctopus

One EmailOctopus list holds everyone who asked for email: people who got the font
from the font page, and Guqin Tabs users who ticked "Email me Guqin Tabs updates"
(guqintabs.com adds them through the API, tagged `gt-users`). Segments are built
from tags and form answers, so the font page's subscribers keep the segments
they had in MailerLite (each MailerLite group came over as a tag). The free plan
allows 2,500 contacts, 10,000 emails a month, 3 automations and 10 tags per list.

**Tags, choices and segments.** A tag is a label on a contact (where they came
from: `JZPDownload`, `gt-users`, and the old MailerLite groups). A choice field is
a question on the form; the font page's "I am a…" is one, set to allow several
answers (Musician, Engineer, …), and people can change their answers from the
link in every email. A segment is a saved rule you send a campaign to, matching
any, all or none of its conditions: "Engineers and musicians" is *any* of has
tag Engineer, has tag Musician, I am a… includes Engineer, includes Musician, so
subscribers from MailerLite (tags) and new ones (answers) land in the same
segment.

**The font page's form.** The Download button opens an EmailOctopus sign-up form
in a dialog. Its id is `window.EO_FORM_ID` near the top of `site/index.html`:
the id in the form's embed code (`https://eocampaign1.com/form/<id>.js`). With
the id empty, Download just downloads the font. In EmailOctopus:

- The form (Forms → the form → Settings) adds its subscribers to the list with
  the tag `JZPDownload` (click the email field, then Tags), and asks "I am a…" as
  a choice field allowing several answers, with the same options as the
  MailerLite form's groups.
- A segment, **JZPDownload**: has tag `JZPDownload` (plus, for subscribers who
  came from MailerLite, their old download group's tag, or bulk-tag them).
- An automation, triggered by "Contact tagged" `JZPDownload`, sends the email with
  the download link. That link must be `https://jianzipufont.com/JianZiPu.ttf`,
  or `https://github.com/neuralfirings/JianZiPu/releases/latest/download/JianZiPu.ttf`.
  Both always serve the newest release, so the email never needs editing. Don't
  link to a release candidate.

**Moving from MailerLite (once).** Contacts → Import → MailerLite, connected with
a MailerLite API key, brings the subscribers and their groups (as tags). Or
export from MailerLite with the Groups column (Set columns → Groups) and import
the CSV, mapping that column with "Import comma-separated tags". Then rebuild
each MailerLite segment in EmailOctopus as a segment matching *any* of the old
group's tag and the matching "I am a…" answer. Bulk-tag the imported downloaders
`JZPDownload` (Contacts → select → Add tag) *before* turning the download
automation on, or they would all get the download email again.
