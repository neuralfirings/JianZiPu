# Reviewing Change Requests

Testers improve the font in the online Builder (builder.jianzipufont.com). Each
tester works in a private **draft**. When some of their changes are ready, they
send them as a **Change Request** (a CR). The maintainer decides on each change
on the Review screen, in the local Builder or in the online one (where only
admins see Review). Kept changes reach the font only through a release, made in
the **local** Builder ([releasing.md](releasing.md)).

```
tester (online Builder)          maintainer (Review: online or local; Release: local)
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
  undo them. Everything else in the draft stays editable, and a change you skip
  unlocks as soon as you save your decisions.
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
2. Open Review, in either Builder. Online (builder.jianzipufont.com), the
   **Review** tab shows once you're signed in with an account whose `role` in
   `profiles` is `admin`; testers don't see it. Your decisions are saved in
   Supabase, so the local Builder's Release screen finds them later. Locally:
   start the local Builder and open http://127.0.0.1:5713/review. Sign in with
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
   A change your Builder has also changed since the request was sent (on main,
   or by a request you tried) is marked **Changed in your Builder too**, with
   before, the request's version and yours side by side (for a word type, **Show
   JSON changes** compares yours with the request's); **Conflicts** lists them.
   Keep or Skip it as usual: **Add kept changes** asks which version wins when
   the release takes it. "Your Builder" is your files plus any unsaved changes,
   so undo tried requests first: while a request's own changes are in your
   Builder, nothing in it shows as a clash.
4. **Try it** (optional). **Try in Build & test**, beside Save decisions, brings
   the changes ticked Keep into your Builder as unsaved changes, one undo step,
   and opens Build & test on the request's words (each new glyph's spelling and
   its glossary example). Use **Test the design**: it draws them live and saves
   nothing. Don't press **Save & build**: on your computer it saves first, which
   writes the tried changes into the font files. Online, your own draft saves
   as you go, so the tried changes stay in it until you Undo them. To try several requests
   together, go back and press it on each; every request is its own undo step.
   **Undo** (once per request) takes them back out; the header returns to
   **Saved**. A change your Builder already has is left alone; one your Builder has
   changed too (main since the request was sent, or another request you
   tried) comes in as the request has it, so you see the request's version; the
   message names them ("this one replaces what your Builder had …: Word type ·
   chord"). To see how they differ, Undo, then use **Conflicts** on the request's
   page (step 3). Undo before you **Save** anything else, or the tried changes
   are saved with it.
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
     a draft down. To take one down, **Delete…** it in Review › Glossary drafts (below).
   - If the After drawing shows the word in pieces, the new glyph fits no word
     type: it's in no area, or the design's spacing rules don't name it. That's
     the tester's draft to fix; Build & test's warning says which.
7. If you like, write a reply. The tester sees it on Your Change Requests and in
   the email.
8. **Save decisions.** The request becomes **In review** and its author gets an
   email. If you skipped everything, it becomes **Declined** instead. Keep /
   Skip and the reply stay on the page until then: leaving the request first
   asks whether to save them.

Saving decisions doesn't change the font or your files. The kept changes wait
for the next release candidate. Until then, you can open the request again and
change your decisions.

**Sending changes back** (a missing definition, say): write what's needed in the
reply, **Skip** those changes, then **Save decisions**. Every skipped change
unlocks in the tester's draft as soon as you save, so they can fix it and send
it in a new request; the kept ones stay locked and go on to the release. Skip
all and the request becomes Declined, everything unlocks, and the tester gets
your reply either way. There's no "needs changes" status.

**Withdraw**: a tester can withdraw a request until you keep one of its
changes. Keeping one (and saving) takes Withdraw away; the database enforces it
too.

To try kept changes together, use the Release screen's **Add kept changes** on
a release branch ([releasing.md](releasing.md)). Or open the tester's current
draft (below) and **Apply** it, then look in Build & test's **Test the design**
without saving.

## Feedback and Glossary drafts

Review has two more tabs for admins, online and local:

- **Feedback**: the font page's messages (the `feedback` table) as an inbox,
  with their pictures from the private `feedback` bucket. Set a status (New,
  Read, Need info, WIP, Done, Won't do), a ticket link (whatever the
  status) and your own note. Opening a New message marks it Read. A character
  request set to **WIP** adds its coming character (the
  `feedback_take_on` trigger) when none is linked yet. Under **Coming
  character** a message shows its linked character as the font page will;
  **Link…** links it to an existing one (a duplicate request) or makes a **New
  coming character** from it, and **Unlink** takes the link off. Each message
  shows a short id (`#a1b2c3d4`, **Copy** for a "dup of feedback …" note), and
  **Find** looks one up by it or by its words. The admins' email for each
  message opens it here.
- **Glossary drafts**: every row of `upcoming`, by stage, each shown as the
  font page will show it: in its section's table (read from `/site/`), between
  the rows around it.
  **Edit** changes the words, section, place (`after`), stage, version or the
  public note; **Delete…** removes the row and its drawing. A row without a
  section isn't on the font page.

Use these screens rather than the Supabase dashboard: they show the pictures
and the page, and write the same rows.

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
v3.300". Its skipped changes unlock in their draft as soon as you save your
decisions (a declined or withdrawn request unlocks everything), so they can
keep working on them; the kept ones stay locked until the release. If you open
the request again and switch a skipped change to Keep, the request's own copy
of it is what goes into the font, not the tester's later edits.

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
