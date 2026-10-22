// Small shared state for the pilot screens: which pilot dialog is open, the draft the Review
// screen shows, the owner's "reviewed" marks (this browser only), and the .zip download.
import { toZip, zipName, type Bundle } from './bundle';

export type PilotDialog = 'welcome' | 'export' | 'import' | 'discard' | 'update' | null;
export type ReviewSource =
  | { kind: 'zip'; name: string }
  | { kind: 'draft'; name: string; uid: string; stamp: string }
  | { kind: 'mine'; name: string };

class Pilot {
  dialog = $state<PilotDialog>(null);
  /** The font-updated banner was dismissed (once per sign-in). */
  updateDismissed = $state(false);
  /** A one-line note after an action ("Saved lg_gou to your draft…"), with an optional Undo. */
  toast = $state<{ text: string; undo?: boolean; copy?: string } | null>(null);
  review = $state<{ bundle: Bundle; source: ReviewSource } | null>(null);

  say(text: string, o: { undo?: boolean; copy?: string } = {}) {
    this.toast = { text, ...o };
  }
}
export const pilot = new Pilot();

const WELCOMED = 'jzp-pilot-welcomed';
export function welcomed(uid: string): boolean {
  try { return localStorage.getItem(`${WELCOMED}:${uid}`) === '1'; } catch { return true; }
}
export function markWelcomed(uid: string) {
  try { localStorage.setItem(`${WELCOMED}:${uid}`, '1'); } catch {}
}

const REVIEWED = 'jzp-reviewed';
/** uid -> {stamp of the draft reviewed, when}. */
export function reviewedMarks(): Record<string, { stamp: string; at: string }> {
  try { return JSON.parse(localStorage.getItem(REVIEWED) ?? '{}'); } catch { return {}; }
}
export function markReviewed(uid: string, stamp: string) {
  try { localStorage.setItem(REVIEWED, JSON.stringify({ ...reviewedMarks(), [uid]: { stamp, at: new Date().toISOString() } })); } catch {}
}

export function downloadZip(b: Bundle) {
  const blob = new Blob([toZip(b) as BlobPart], { type: 'application/zip' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = zipName(b);
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/** "18 Oct" */
export const day = (iso: string | Date | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString([], { day: 'numeric', month: 'short' }) : '';
/** A font the way a tester knows it: its version ("3.200"), else its date ("the font of 19 Oct"). */
export const fontName = (v: { version?: string | null; date?: string | null } | null | undefined) =>
  v?.version ? v.version : v?.date ? `the font of ${day(v.date)}` : 'the font';
export const hhmm = (iso: string | Date | null | undefined) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
