# Maintainer setup

The one-time setup behind the Builder, the pilot, and releases. Each part says
where the settings live. Secrets never go in this repository.

| Part | What it does | Where |
| --- | --- | --- |
| Your computer | The local Builder: Review, releases, git | this repo, `builder/.env` |
| Supabase | Sign-in, drafts, Change Requests, the base font, emails | supabase.com dashboard, `supabase/` |
| Railway | The online Builder at builder.jianzipufont.com | railway.com, `Dockerfile` |
| Google Cloud Run | The backup online Builder, and a preview of each pull request | console.cloud.google.com, `.github/workflows/cloudrun.yml`, `deploy/` |
| Resend | Sends the Change Request emails | resend.com, `supabase/functions/notify/` |
| GitHub | Code, tags, releases, the ruleset on main | repository Settings, `.github/workflows/` |
| Cloudflare Pages | The font page at jianzipufont.com | dash.cloudflare.com, `site/` |
| MailerLite | The "send me the font" email on the font page | mailerlite.com |

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

## Google Cloud Run (the backup, and pull request previews)

The same `Dockerfile` runs on Cloud Run as two services, deployed by
`.github/workflows/cloudrun.yml`:

- **`jzp-builder`**, the backup of the online Builder. It deploys `main` on
  every merge, like Railway, so it is ready when Railway isn't.
- **`jzp-builder-staging`**, a preview of each pull request at its own address
  (`https://pr-<number>---jzp-builder-staging-….run.app`). It deploys on every
  push to the pull request, shows as "View deployment" on the pull request,
  and its address is removed when the pull request closes. Pull requests from
  forks get no preview.

Both run one instance at most, because a tester's builds live in the
instance's memory. They stop when nobody uses them, so an idle backup costs
almost nothing; the first visit after a quiet spell waits a few seconds while
it starts.

Previews use the production Supabase project for now, so a preview signs
you in to your real account and reads and writes your real draft. Sign in to
previews only as yourself, and remember a preview's code isn't merged yet: a
bug in it can change your draft. To give previews their own project later, do
the [Supabase](#supabase) steps in a new one and run the setup script again
with its settings for staging.

1. **Google Cloud.** Create a project with billing turned on, install
   `gcloud`, sign in (`gcloud auth login`), then run from the repository:

   ```bash
   PROJECT=<project id> REGION=us-central1 bash deploy/cloudrun-setup.sh
   ```

   It asks for production's `SUPABASE_URL`, `SUPABASE_ANON_KEY` and
   `SUPABASE_SERVICE_KEY` (Supabase → Project Settings → API Keys); press
   Enter at staging's first question to use the same project. The service
   key goes into Secret Manager, never into GitHub. Run it again to change a
   setting; Enter at the service key prompt keeps the stored one.
   GitHub signs in to Google with Workload Identity Federation, limited to
   this repository, so there is no Google key to keep either.
2. **GitHub.** Settings → Secrets and variables → Actions → Variables: add the
   four variables the script prints (`GCP_PROJECT_ID`, `GCP_REGION`,
   `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA`). Until they exist the workflow does
   nothing. Then Actions → cloudrun → Run workflow, on `main`, for the first
   production deploy.
3. **The backup address.** Give the backup a name of its own, so it is ready
   before it's needed (Railway keeps `builder.jianzipufont.com`):
   - `gcloud domains verify jianzipufont.com` (once, in Google Search Console);
   - `gcloud beta run domain-mappings create --service jzp-builder --domain builder-backup.jianzipufont.com --region us-central1`;
   - in Cloudflare DNS, a CNAME `builder-backup` → `ghs.googlehosted.com`,
     **DNS only** (grey cloud). The certificate follows within the hour.
4. **Sign-in addresses.** Supabase only sends sign-in links back to allowed
   addresses (Authentication → URL Configuration → Redirect URLs). Add:
   - `https://builder-backup.jianzipufont.com/**`;
   - the preview pattern: open the first preview, copy its address and put
     `*` in place of `pr-<number>`, for example
     `https://*---jzp-builder-staging-abc123-uc.a.run.app/**`.

### When Railway is down

1. Tell testers to use https://builder-backup.jianzipufont.com. Their drafts
   are in Supabase, so everything they saved is there; work left unsaved in a
   tab on the other address stays in that tab.
2. If the backup is behind `main` (a deploy failed), Actions → cloudrun → Run
   workflow on `main`.
3. For a long outage, move the main name over: create the domain mapping for
   `builder.jianzipufont.com` as in step 3, point its CNAME at
   `ghs.googlehosted.com` (DNS only), and set the `notify` function's
   `BUILDER_URL` if the emails should link to the backup meanwhile. Move it
   back the same way.

## Change Request emails (Resend)

`supabase/functions/notify/README.md` has the full steps. In short:

1. Create a Resend account, add and verify the `jianzipufont.com` domain (DNS
   records), and create an API key.
2. Set the secrets with
   `supabase secrets set RESEND_API_KEY=… MAIL_FROM=… NOTIFY_WEBHOOK_SECRET=… BUILDER_URL=… REVIEW_URL=…`.
3. Deploy with `supabase functions deploy notify --no-verify-jwt`.
4. Create a Database Webhook on `change_requests` (Insert and Update) that calls
   `notify` with the header `x-webhook-secret`.

The email templates are in git (`supabase/functions/notify/templates.ts`). To
change one, edit it, run `deno test supabase/functions/notify`, and deploy
again.

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
- `site/_headers` keeps caches short: `version.json` is never cached and
  `JianZiPu.ttf` for an hour, so people get a new release soon after it
  deploys.

## MailerLite

The signup form on the font page sends an email with the download link. That
link must be `https://jianzipufont.com/JianZiPu.ttf`, or
`https://github.com/neuralfirings/JianZiPu/releases/latest/download/JianZiPu.ttf`.
Both always serve the newest release, so the email never needs editing. Don't
link to a release candidate.
