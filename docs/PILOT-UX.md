# Hosted pilot: summary

Wireframes: `docs/pilot-ux.html` (open it in a browser; it uses no external resources).
Approved by the owner 2026-10-18 with the answers at the end; implemented in `app/` (hosted mode, `/review`). The hosting model is decided (ROADMAP "Pilot hosting"):
Railway serves the font as on main, read-only; invited testers sign in with a Supabase magic link; each
tester has a private draft in Supabase. This is the experience on top of that.

## Decisions

1. **One noun: "your draft".** The tester's work is *your draft*; main is *the font* (dated: "the font of 18 Oct").
   Testers never see main, branch, commit, merge, sync or copy. A proposal starts as a draft later, so the words survive (table below).
2. **Hosted and local differ by one pill.** Hosted: blue `✎ Your draft` pill, Feedback link, person menu. Local:
   dashed `Local files` pill and a fifth nav item, **Review**. Everything else (screens, panels, undo, ⌘S) is unchanged.
3. **Save = save to your draft.** Same Save button and chip. Autosave every 30 s while there are unsaved edits, on screen
   change and on tab close. The browser draft (today's) stays as the offline buffer. Undo survives saves.
   The glyph editor's **Save glyph** also saves into the draft; autosave covers an open glyph too.
4. **Font updated:** a blue info banner once per sign-in, never a block. *Not now* leaves a quiet "font updated" on the pill.
   *Update my draft…* opens one dialog: what comes in on its own (collapsed), and one row per conflict with
   **Keep mine / Take the font's**, shown as pictures (glyphs), sample words (design items) or cells (spellings).
   Conflicts default to *Keep mine*. Update is one undo step and saves. Changes that are already in the font drop out quietly.
   Glyphs the tester never touched already show the font's current outline (the draft only stores changed SVGs).
5. **Conflict units:** a glyph, one spelling cell, an area, a word type, the page center. Different cells of one spelling row merge.
6. **Export = a .zip:** `manifest.json` (who, when, based-on font version, format version), `design.json`, `components.csv`,
   `svg/` (changed and added glyphs only, plus a deleted list in the manifest), and `base/` (the based-on versions of those files),
   so a review can do base / theirs / current without git. Unsaved edits are included.
7. **Import = review.** A .zip always opens the review page (keep/skip, Apply → unsaved edits). Local Import still takes a
   .json for today's design-only import.
8. **Review (local, `/review`)** is one component with three uses: Nancy reviewing a draft, a tester importing a .zip,
   and (read-only) a tester's **See my changes**. Sections Glyphs / Spellings / Design, one item per row, Keep by default,
   conflicts unpicked until chosen; Apply is disabled until every conflict has a pick. A glyph and its spelling row travel together.
   Design items show a plain-language summary first, then before/after sample words (the Area Properties minis), then a folded JSON diff.
9. **Apply** puts everything, glyph files included, into Nancy's unsaved changes ("From Mei: …" in the change list).
   Save writes design.json, components.csv and the SVGs; the toast offers **Copy commit message** and **Undo**. The draft is marked "reviewed <date>".
10. **Sign-in:** one field, magic link valid 1 hour, session 30 days. Unknown email gets a plain "not on the pilot list" page (see Q1).

## Copy

### Sign-in
| Where | Text |
|---|---|
| Title | JZP Font Builder · pilot |
| Lead | For invited testers. Type the email Nancy invited, and we'll send you a link to sign in. No password needed. |
| Button | Email me a sign-in link |
| Footer link | Want to try it? Ask for an invite ↗ |
| Sent: title / body | Check your email · We sent a sign-in link to {email}. Open it on this computer, in this browser. |
| Sent: help | The link works once, for 1 hour. Nothing there? Look in spam, or send it again. |
| Sent: buttons | Send again (0:24) · Use a different email |
| Not invited | This email isn't on the pilot list · {email} wasn't invited. The pilot is for a few invited testers for now. If Nancy invited you at another address, use that one. · Try another email · Ask for an invite ↗ |
| Expired | This sign-in link has expired · Links work once, for 1 hour. Send yourself a new one. · Email me a new link |

### Header (hosted)
| Element | Text |
|---|---|
| Pill | ✎ Your draft · tooltip "Only you see your draft. The font itself doesn't change." |
| Pill, font moved and Not now | ✎ Your draft · font updated |
| Chip states | ● 3 unsaved · Saving… · Saved to your draft · 14:02 · ⚠ Not saved · offline |
| Save button | Save (tooltip "Save to your draft (⌘S). It also saves itself every 30 seconds.") · Saving… · Try again (offline) |
| Link | Feedback |
| ⋯ menu | Export my draft (.zip)… · Import a draft (.zip)… · Update my draft to the font… (greyed "up to date") · Send feedback ↗ · Welcome note · Reset panel layouts · Discard my draft… |
| Person menu | Signed in as {email} · Sign out |
| Popover | Your draft · Only you see it. Builds and the Tester use it. The font itself doesn't change. · Based on the font of 15 Oct · last saved 14:02 · Your changes: 2 glyphs · 5 spellings · 2 design items · See my changes · Export… |
| Glyph editor toast | Saved lg_gou to your draft. Layouts and the Tester use it now. |

Local header: pill `Local files` (tooltip "Save writes design.json, components.csv and glyph files in this repo."), nav item **Review**,
⋯ adds **Review a draft…**. Local Export adds **Download as draft .zip**.

### Welcome note (first sign-in; ⋯ → Welcome note)
Title **Welcome, {first name}**. "Thank you for testing the JZP Font Builder. Three things to know:"
1. **This is your own draft.** Change anything: glyphs, how they're typed, how words are laid out. Nothing you do changes the real font or anyone else's work.
2. **It saves itself** every 30 seconds, and when you press Save. ↶ undoes a step.
3. **Tell us what you think.** Confusing, broken or lovely: Feedback (top right) takes a minute. To share your work itself, ⋯ → Export my draft.

Small print: "Good places to start: Tester (type a few words), then Glyphs → open a glyph → Edit." Buttons: **Open the Tester** · **Start**.

### Font updated
| Element | Text |
|---|---|
| Banner | **The font was updated on 18 Oct** (since your draft started on 15 Oct): 3 glyphs, 6 spellings, 1 word type. · What changed? · Not now · Update my draft… |
| Dialog title | Update your draft to the font of 18 Oct |
| Dialog lead | The font has {n} changes since 15 Oct. {a} are in things you didn't change: they come in on their own. {c} are in things you also changed: choose which to keep. |
| Aside | 1 of your changes is already in the font (thank you!) and leaves your list. |
| Row badge / choices | both changed · Keep mine · Take the font's · labels "yours", "the font's new one", "before (15 Oct)" |
| Word-type hint | A word type is one item: you keep one side whole. Export first if you want both and redo one by hand. |
| Fold | {a} changes that come in on their own |
| Buttons | Export my draft first · Not now · Update my draft |
| Toast | Your draft is now based on the font of 18 Oct. 8 changes came in; you kept 2 of yours. · Undo |

### Export / Import / Discard
| Dialog | Text |
|---|---|
| Export | **Export your draft** · One .zip with everything in your draft. Send it to Nancy, or keep it as a backup: ⋯ → Import opens it again. · (file list) · Includes unsaved edits too (3 right now), so what you download is what you see. · Cancel · Download .zip |
| File name | `jzp-draft-{first name}-{yyyy-mm-dd}.zip` |
| Import | **Import a draft** · Open a draft .zip (yours, or one someone sent you). You'll see every change before anything goes into your draft. · Drop a .zip here, or choose a file · Cancel |
| Discard | **Discard your draft?** · This deletes your draft and starts you again from the font of 18 Oct. You'd lose 2 glyphs, 5 spellings and 2 design changes. It can't be undone. · Want to keep a copy? Export it first. · Export first · Cancel · **Discard my draft** (red) |

### Review
| Element | Text |
|---|---|
| Page title | Review a draft · Open a .zip… |
| List columns | Tester · Last saved · Based on · Changes · Status |
| Based-on tag | {n} update(s) behind |
| Status | new since you looked · reviewed 18 Oct · (empty) |
| Row actions | Review · .zip |
| Signed out | Sign in to see testers' drafts (admin emails only). Open a .zip works without signing in. |
| Review header | {Name}'s draft · saved today 14:02 · based on the font of 15 Oct · your Builder is on 18 Oct · All 9 / Conflicts 1 / Skipped 2 · Keep all · Skip all |
| Item badges | added · changed · deleted · conflict · clashes with {glyph} |
| Item controls | Keep / Skip · Open in glyph editor · Open in Layouts · Show JSON changes ({n} lines) |
| Glyph views | before · after · before / after (overlay) · in a word, after |
| Conflict columns | Before (15 Oct) · {Name}'s draft · Your Builder now · Use before · Use {Name}'s · Keep yours · "pick one to apply" |
| Apply bar | Keeping 6 of 9 · 1 conflict to pick · Applied changes become unsaved changes in your Builder. Nothing is written until you Save. · Cancel · Apply 6 changes (disabled tooltip "Pick 1 conflict first") |
| After Apply | Applied 6 changes from Mei Chen's draft. They're unsaved: look them over, then Save and commit. · Copy commit message · Undo |
| Commit message | Apply Mei Chen's draft: lg_gou, 3 spellings, Standard word spacing |
| Tester's own (See my changes) | Your changes · same sections, no Keep/Skip, no Apply · Export… |
| Tester import | Import into your draft · Apply → "Applied 6 changes from {file}. They're unsaved until Save (or the next autosave)." |

### Errors and empty states
| State | Text |
|---|---|
| Can't save | ⚠ **Your draft isn't saved.** We can't reach the server. Your changes are kept in this browser and will save when you're back online. Don't close this browser's private window or clear its data. · Try again · Export my draft |
| Back online | Saved to your draft. |
| Saved elsewhere | **Your draft was saved somewhere else** · Another tab or computer saved your draft at 14:05, after you opened it here. Which one should stay? · Export this one first · Load the 14:05 version · Keep this one |
| Signed out | You've been signed out. Your unsaved changes are kept in this browser. · Sign in again |
| Restored | Restored 3 changes from your last visit that hadn't reached your draft. · Save them · Discard them |
| Review: none | No tester has saved a draft yet. Drafts appear here after a tester's first save. You can still open a .zip. |
| Wrong file | "{file}" isn't a Builder draft: it has no manifest.json. · Choose another file |
| Too new | This draft was made with a newer Builder. Update this Builder first. |
| Build failed | The font couldn't be built from your draft. · Show details · Send this to Nancy ↗ (feedback form with the build id, nothing else, in the URL) |
| Server down | **The Builder is taking a break** · We can't reach it right now. Your saved draft is safe. Try again in a few minutes. · Try again |

## States (hosted)

| State | Header chip | Save | Notes |
|---|---|---|---|
| Clean | Saved to your draft · 14:02 | disabled | |
| Dirty | ● n unsaved | Save | autosave in ≤ 30 s |
| Saving | Saving… | Saving… (disabled) | |
| Offline / error | ⚠ Not saved · offline | Try again | red banner; retries every 30 s; Build/Tester use the browser copy |
| Conflict (other tab) | as dirty | Save | dialog on next save |
| Font moved, not updated | pill "· font updated" | as above | banner once per sign-in |
| Signed out mid-work | as dirty | disabled | banner, Sign in again |

## Words that survive the move to proposals

| Pilot | Later |
|---|---|
| Your draft | Your proposal (draft) |
| Saved to your draft | Saved to your proposal |
| The font of {date} | The font (released) |
| Update my draft | Update your proposal |
| Review a draft · Keep / Skip · Apply | Review a proposal · Keep / Skip · Approve |
| See my changes | The proposal page |
| Export / Import .zip | Unchanged (backup, offline path) |

## Left out on purpose

Comments and conversations (feedback form instead), per-rule conflict picks inside a word type, sharing a draft with another tester,
version history of a draft, notifications, roles. Testers can't see each other's drafts.

## Owner's answers (2026-10-18)

1. Not invited: say it plainly ("This email isn't on the pilot list yet — ask Nancy for an invite").
2. Conflict unit: a whole word type or area at a time for the pilot; per-rule picks are v2.
3. On Apply, glyph files wait for Save with everything else (Undo and Discard undo a merge).
4. Review is a fifth item in the top bar, local mode only.
5. Testers get the read-only "See my changes".
6. Testers resolve their own Update conflicts (Keep mine / Take the font's).

## Open questions (answered above)

1. Not invited: say plainly "This email isn't on the pilot list" (proposed, friendlier), or the neutral "If you're invited, a link is on its way" (doesn't reveal who's invited)?
2. Conflict unit: a whole word type or area is kept from one side. Fine for the pilot, or do you need per-rule picks inside a word type?
3. On Apply, glyph files wait for Save with the rest (proposed), or write at once like the glyph editor's Save glyph?
4. Review as a fifth nav item in local mode (proposed), or only ⋯ → Review a draft?
5. Should testers get "See my changes" (read-only review of their own draft) in the pilot, or is the unsaved list enough until proposals?
6. Are testers trusted to resolve their own Update conflicts (proposed), or should a conflicted update wait for you?
