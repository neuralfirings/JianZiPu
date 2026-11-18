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
- A new glyph for a character on the font page's **Coming next** is tagged with
  it (**Is this for a coming character?**, suggested from its spelling), so you
  can put its drawing on the page (step 6 below).
- Sent changes are **locked** in their draft. They can see them but not edit or
  undo them. Everything else in the draft stays editable.
- Your Change Requests (`/requests`) shows each request's status, your reply,
  and what was sent. They can **Withdraw** a request until you keep one of its
  changes.
- They get an email at every status change (from the `notify` function), with
  your reply in it.
- Your Change Requests lists open requests first, then **Released** and
  **Declined or withdrawn**, each folded.

## Reviewing

1. You get an email ("New Change Request: …") with a link to Review. (No email?
   The `notify` function and its webhook must be set up: see
   [setup.md](setup.md), "Change Request emails".)
2. Start the local Builder and open http://127.0.0.1:5713/review. Sign in with
   your admin email (a magic link). The list shows the open requests; the
   filter shows the rest. Work on `main` (or the PR branch you're testing) with
   a rebuilt app: `git pull`, then `cd app && npm run build`, then restart the
   web server.
3. **Review** a request. You see:
   - at the top: who sent it, their notes, and how they want to be credited;
   - **On the glossary** (when it adds glyphs with a glossary row; step 6);
   - then each change, before and after: glyphs drawn over each other,
     spellings side by side, design changes with sample words and the JSON, and
     glossary rows before and after, each with its example under it. Each row
     added, taken out or edited is a change of its own, and a kept new row goes
     between the same rows as in the draft; a subtitle's title, description,
     example and row order are one more change, and a new or removed subtitle is
     one change with its rows.
4. **Try it** (optional). **Try in Build & test**, beside Save decisions, brings
   the changes ticked Keep into your Builder as unsaved changes, one undo step,
   and opens Build & test on the request's words (each new glyph's spelling and
   its glossary example). Use **Test the design**: it draws them live and saves
   nothing. Don't press **Save & build**: on your computer it saves first, which
   writes the tried changes into the font files. To try several requests
   together, go back and press it on each; every request is its own undo step.
   **Undo** (once per request) takes them back out; the header returns to
   **Saved**. A change your Builder already has, or one that clashes with a
   change made since the request was sent, stays out (the message says how
   many). Undo before you **Save** anything else, or the tried changes are
   saved with it.
5. Choose **Keep** or **Skip** for each change, or **Keep all**. A new glyph
   goes together with its spellings and its place in an area. An area's box,
   advance and label are one change, and each glyph that joins or leaves the
   area is a change of its own, so you can keep some new members and skip
   others (a new or removed area is one change, members and all). A request
   sent before this split lists an area whole; Review shows it as these
   changes, each with the decision the area had. Likewise a request sent while
   a glossary subtitle was one change shows as its rows, each with the
   subtitle's decision.
6. **On the glossary** (optional): show the request's drawings on the font page
   now, as drafts experts can comment on, before you decide on the release.
   - Each new glyph with a glossary row is listed with the coming character it
     draws: the tester's tag (**Is this for a coming character?** when they
     sent it), the row it's already in if you published it before, or **A new
     row on the page**. Change it if it's wrong.
   - **Now** is its row on the font page today; **After** is how it will look:
     its spellings, the definition, where it goes, and the example Glyphs ›
     Glossary shows for it (its own, like 引上九; else its section's default,
     like 散抹勾五; else the row typed on its own), as the font sets it, red
     where the page puts red.
   - **Publish draft to glossary** uploads each example to the public `upcoming`
     bucket and writes its row in the `upcoming` table (stage `draft`); the font
     page shows it as **Draft design** within a minute. Publishing again (**Update
     the draft on the glossary**, or the same glyph in a later request) updates
     the same row; it never adds a second one.
   - It doesn't depend on your decisions, and declining the request doesn't take
     a draft down. To take one down, delete its row in Supabase (below).
   - If the After drawing shows the word in pieces, the new glyph fits no word
     type: it's in no area, or the design's spacing rules don't name it. That's
     the tester's draft to fix; Build & test's warning says which.
7. If you like, write a reply. The tester sees it on Your Change Requests and in
   the email.
8. **Save decisions.** The request becomes **In review** and its author gets an
   email. If you skipped everything, it becomes **Declined** instead.

Saving decisions doesn't change the font or your files. The kept changes wait
for the next release candidate. Until then, you can open the request again and
change your decisions.

**Sending a request back for changes** (a missing definition, say): write what's
needed in the reply, **Skip all**, then **Save decisions**. The request becomes
Declined, the tester gets your reply, and all its changes unlock in their draft
so they can fix them and send a new request. There's no "needs changes" status:
keeping some and skipping others leaves the request In review, and an In review
request keeps all its changes locked in the tester's draft until a release
candidate takes it.

**Withdraw**: a tester can withdraw a request until you keep one of its
changes. Keeping one (and saving) takes Withdraw away; the database enforces it
too.

To try kept changes together, use the Release screen's **Add kept changes** on
a release branch ([releasing.md](releasing.md)). Or open the tester's current
draft (below) and **Apply** it, then look in Build & test's **Test the design**
without saving.

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
v3.300". Its skipped changes unlock in their draft once it goes into a release
candidate (a declined or withdrawn request unlocks everything at once), so they
can keep working on them.

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
get an email. In the online Builder:

- The released changes fold away on Your changes, under **In the font now**.
- The requests move to **Released** on Your Change Requests (declined and
  withdrawn ones are under **Declined or withdrawn**).
- Testers see "JianZiPu 3.300 is out", with **Set reference font to 3.300
  (latest)…**. A tester's draft is compared with a reference font (a
  release), and this moves it to the new one: the released changes leave
  Your changes, and anything still unsent stays.

Released changes aren't locked. They're the font's now, and a tester can change
them again in a new Change Request.
