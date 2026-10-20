# Supabase auth emails

The HTML and subject of every Supabase auth email, kept in git so changes are
reviewed and the dashboard can be rebuilt from here. Supabase does not read
this folder: after changing a template, paste it into the dashboard by hand.

| File | Dashboard name | Sent by the pilot |
| --- | --- | --- |
| `invite.html` | Invite user | Yes, when an admin invites a tester |
| `magic_link.html` | Magic Link | Yes, every sign-in |
| `confirm_signup.html` | Confirm signup | No, sign-ups are off |
| `change_email.html` | Change Email Address | No |
| `reset_password.html` | Reset Password | No, sign-in is by email link |
| `reauthentication.html` | Reauthentication | No |

Subjects live in `templates.json`, because Supabase stores them apart from the
HTML.

## Preview

```bash
cd supabase/emails && python3 -m http.server 8000
```

Then open http://localhost:8000/preview.html. Pick a template, and the middle
column lists the variables it uses with a box for each. Type your own values
and the preview updates; they stay in that browser. **Open a file** previews
any template HTML, such as one copied out of the dashboard. **Copy template**
and **Copy subject** copy the raw text, variables intact, ready to paste.

Opening `preview.html` straight from disk only allows **Open a file**, since a
browser will not let a local page read the files beside it.

## Publishing a change

1. Edit the HTML here, or the subject in `templates.json`, and check it in the preview.
2. Supabase dashboard → Authentication → Emails → the template's tab.
3. Paste the subject and the HTML (the preview's copy buttons), then Save.
4. Commit the change here.

## Variables

Supabase fills these Go template variables when it sends an email:

| Variable | What it is |
| --- | --- |
| `{{ .ConfirmationURL }}` | Link that completes the action |
| `{{ .Token }}` | Six-digit one-time code |
| `{{ .TokenHash }}` | Hashed token, for building your own link |
| `{{ .SiteURL }}` | The project's Site URL |
| `{{ .Email }}` | The user's current address |
| `{{ .NewEmail }}` | The new address, change email only |
| `{{ .RedirectTo }}` | Redirect address the app asked for |
| `{{ .Data.<key> }}` | The user's metadata |

The preview fills plain `{{ .Name }}` values. Logic such as `{{ if … }}` is
shown as written, with a note above the variables.

## Writing templates

Email clients ignore most CSS, so the templates use tables and inline styles,
with the Builder's colours written out as hex values. Web fonts are named with
Georgia as the fallback, which is what most clients will show. Keep to the
Builder's voice: sentence case, no exclamation marks. `builder/tests/test_emails.py`
checks every listed file exists and uses only Supabase's variables.
