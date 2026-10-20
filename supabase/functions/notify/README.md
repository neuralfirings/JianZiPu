# Change Request emails

A Supabase Edge Function that emails people when a Change Request moves
(`supabase/004_change_requests.sql`), sent through [Resend](https://resend.com).
The templates are in git, in `templates.ts`, so they are reviewed like any other
change; nothing is stored on the Resend dashboard.

| When | Email | To |
| --- | --- | --- |
| A tester sends a Change Request | `new_request` | every admin (`profiles.role = 'admin'`) |
| A tester withdraws one | `withdrawn` | every admin |
| An admin reviews it, declines it, or it goes into a release candidate or a release | `status_changed` | the tester who sent it |

`events.ts` decides which email a database change sends; `templates.ts` writes the
subject, plain text and HTML (the same look as the auth emails in `supabase/emails/`);
`index.ts` looks up the addresses and sends.

## Setting it up

1. **Resend**: an account, the domain `jianzipufont.com` added and verified (it lists
   the DNS records to add), and an API key with sending access.
2. **Secrets** (the Supabase CLI, linked to the project):

   ```bash
   supabase secrets set RESEND_API_KEY=re_... MAIL_FROM="JZP Font Builder <builder@jianzipufont.com>" \
     NOTIFY_WEBHOOK_SECRET=<a long random string> \
     BUILDER_URL=https://builder.jianzipufont.com REVIEW_URL=http://127.0.0.1:5713
   ```

   `BUILDER_URL` is where testers' links go (Your Change Requests); `REVIEW_URL` is
   where admins review (the local Builder). `SUPABASE_URL` and
   `SUPABASE_SERVICE_ROLE_KEY` are given to every Edge Function by Supabase.
3. **Deploy**: `supabase functions deploy notify --no-verify-jwt` (the webhook proves
   itself with the secret header instead of a user's sign-in).
4. **Webhook**: Dashboard → Database → Webhooks → Create a new hook. Table
   `change_requests`, events Insert and Update, type Supabase Edge Functions,
   function `notify`, method POST, and an HTTP header
   `x-webhook-secret: <the same random string>`.

The API key and the webhook secret live only in Supabase's secrets, never in this repo.

## Changing an email

Edit `templates.ts`, run the tests, then deploy again:

```bash
deno test supabase/functions/notify
supabase functions deploy notify --no-verify-jwt
```
