# Reviewing Change Requests

Testers improve the font in the online Builder (builder.jianzipufont.com). Each
tester works in a private **draft**. When some of their changes are ready, they
send them as a **Change Request** (a CR). The maintainer decides on each change
in the **local** Builder. Kept changes reach the font only through a release
([releasing.md](releasing.md)).

```
tester (online Builder)                 maintainer (local Builder)
  draft ──Send Change Request──▶ Sent ──Review: Keep / Skip──▶ In review ──Build candidate──▶
  In a release candidate ──Publish──▶ Released
                         (all skipped: Declined; the tester can Withdraw until a change is kept)
```

## What a tester sees

The Builder's own help, the "Change Requests" section at `/help#requests`, is
the tester's guide. In short:

- On Your changes (`/review?mine`), they undo single changes, or choose **Send
  Change Request…**. They tick which changes go, then add a title, notes, and
  how they'd like to be credited. **Save as draft** keeps an unfinished request
  for later.
- Before a request goes, the Builder saves the draft, checks the spellings
  don't clash, and builds a font from just those changes. A request that
  arrives has built at least once.
- Sent changes are **locked** in their draft. They can see them but not edit or
  undo them. Everything else in the draft stays editable.
- Your Change Requests (`/requests`) shows each request's status, your reply,
  and what was sent. They can **Withdraw** a request until you keep one of its
  changes.
- They get an email at every status change.

## Reviewing

1. You get an email ("New Change Request: …") with a link to Review.
2. Start the local Builder and open http://127.0.0.1:5713/review. Sign in with
   your admin email (a magic link). The list shows the open requests; the
   filter shows the rest.
3. **Review** a request. You see:
   - at the top: who sent it, their notes, and how they want to be credited;
   - then each change, before and after: glyphs drawn over each other,
     spellings side by side, and design changes with sample words and the JSON.
4. Choose **Keep** or **Skip** for each change, or **Keep all**. A new glyph
   and its spellings go together.
5. If you like, write a reply. The tester sees it on Your Change Requests and in
   the email.
6. **Save decisions.** The request becomes **In review** and its author gets an
   email. If you skipped everything, it becomes **Declined** instead, and its
   changes unlock in the tester's draft.

Saving decisions doesn't change the font or your files. The kept changes wait
for the next release candidate. Until then, you can open the request again and
change your decisions.

To try a change before deciding, keep it, then use the Release screen's **Add
kept changes** on a release branch. Or open the tester's current draft (below)
and **Apply** it, then look in Layouts and Build & test without saving.

## Statuses

| Status | Meaning | Set by |
| --- | --- | --- |
| Sent | Waiting for review | the tester, by sending |
| In review | Decisions saved; kept changes wait for the next release | you, Save decisions |
| Declined | Every change skipped | you, Save decisions |
| Withdrawn | Taken back by the tester | the tester, until a change is kept |
| In a release candidate | Its kept changes are in `v<version>-rc.N` | Build candidate |
| Released | Its kept changes are in `v<version>` | Publish |

A request can be partly kept. The tester sees, for example, "3 of 5 changes in
v3.300". Skipped changes unlock in their draft, so they can keep working on
them.

These rules are enforced in the database (`supabase/004_change_requests.sql`),
not just by the app:

- a tester can only create requests with status Sent;
- a tester can only withdraw while nothing in the request is kept;
- only admins change anything else.

## Testers' drafts, without a request

Below the requests, **Current drafts** lists what each tester is working on
right now, whether or not they've sent it. Someone can also send you a draft
`.zip` (Export from their ⋯ menu); open it with **Open a .zip…**.

Either way, choose Keep or Skip for each change, then **Apply**. The kept
changes become one undoable step of unsaved changes, glyph files included. A
**Conflict** means you changed the same thing since their draft started, so
pick whose version to use.

Changes applied this way skip the request flow: no statuses, no emails, no
credit in the changelog. Use it for your own drafts, or to look at work in
progress. To take the changes, do this on a release branch and **Save** there
([releasing.md](releasing.md)), so the change goes out with a version number
like every other font change.

## After a release

When a release is published, its requests become Released and their authors
get an email. In the online Builder, testers see "The font was updated". **Update
my draft…** brings the new font into their draft: their released changes drop
out of Your changes, and anything still unsent stays.
