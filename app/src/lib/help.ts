// Help text, written once. HELP_SECTIONS is the help page's contents list (one entry per
// section of routes/help/+page.svelte, in page order). PANEL_HELP is what each dockable panel's
// ? shows; the help page renders the same entries in its Layouts and glyph editor sections, so a
// panel's help is edited here and nowhere else. help.test.ts checks every panel has an entry and
// every link lands. When a feature changes, update its entry here (see CLAUDE.md).
import type { PanelId, EditorPanelId } from './panels.svelte';

export const HELP_SECTIONS: { id: string; title: string }[] = [
  { id: 'start', title: 'Getting started' },
  { id: 'typing', title: 'How words are typed' },
  { id: 'glyphs', title: 'Glyphs' },
  { id: 'editor', title: 'The glyph editor' },
  { id: 'layouts', title: 'Layouts' },
  { id: 'build', title: 'Build & test' },
  { id: 'saving', title: 'Saving and undo' },
  { id: 'draft', title: 'Your draft (online)' },
  { id: 'requests', title: 'Change Requests' },
  { id: 'review', title: 'Reviewing Change Requests' },
  { id: 'release', title: 'Making a release' },
  { id: 'keys', title: 'Keyboard shortcuts' },
  { id: 'trouble', title: 'When something looks wrong' },
  { id: 'messages', title: 'Messages and errors' }
];

/** One panel's help: `html` is trusted, static markup (links, <strong>, <kbd>, <code>). */
export type HelpTopic = { title: string; html: string };
export type PanelHelp<Id extends string> = { section: string; topics: Record<Id, HelpTopic> };

/** The help page anchor for one panel's entry, e.g. #layouts-spacing. */
export const helpAnchor = (section: string, id: string) => `${section}-${id}`;

export const LAYOUTS_HELP: PanelHelp<PanelId> = {
  section: 'layouts',
  topics: {
    types: { title: 'Word types', html: 'Pick the word type to edit: a standard note, a vertical word, the two halves of a chord. Each shows how many positioning rules it makes; <strong>skipped</strong> lists shapes that get no rule. With <strong>Advanced</strong> on you can add, duplicate or delete word types.' },
    structure: { title: 'Structure', html: 'The parts of the word type, in order. Tick a part to include it in the example word and pick which glyph it shows. <strong>anchor</strong> marks the first part of the chain, which carries the word\'s position. With <strong>Advanced</strong> on you can add, remove, reorder and make parts optional or repeating.' },
    pagecenter: { title: 'Page center', html: 'The point on the page that centring aims for, in font units. Every word type that is centred uses it.' },
    budget: { title: 'Font budget', html: 'How many positioning rules each word type makes, and an estimate of their size. The build stores each rule as its own small table, so size is far from a limit (a single lookup can hold 65,535). What to watch is <strong>skipped</strong>: word shapes that get no rule because a part has nothing placing it, so those words won\'t be laid out. The <strong>rules · KB</strong> pill in the header opens this panel; it shows <strong>!</strong> while anything is skipped.' },
    spacing: { title: 'Spacing', html: 'How the selected part sits against the others, vertically or horizontally (the <strong>Vertical</strong> and <strong>Horizontal</strong> tabs). A rule reads as a sentence: "its top edge sits at the bottom of 七 + gap". Rows change the gap when certain glyphs are present; <em>otherwise</em> covers the rest. <strong>+ new rule</strong> picks the glyphs it applies to, and the canvas previews every combination. You can also drag the part on the canvas.' },
    centering: { title: 'Centering', html: 'Which parts the word is centred on, and where. When a word is centred on an axis, the whole word is shifted to the target, so a start height on that axis (marked <strong>*</strong> on the canvas) doesn\'t move it: change the gaps between parts instead, or the target here.' },
    glyphs: { title: 'Area Properties', html: 'An area is a set of glyphs that share a box size and can stand in for each other in a word (all the strings, all the hui numbers…). Here: the box size (type to preview, <kbd>Enter</kbd> applies, <kbd>Esc</kbd> cancels), the word types that use the area, and its glyphs (<strong>Manage</strong> to add or remove). <strong>Delete area</strong> works only on an empty area nothing uses. The <strong>Chord divider</strong> and <strong>Vertical marker</strong> areas also have <strong>Width of |</strong> (or <strong>:</strong>): how far the next part moves after the divider, and the divider\'s own width in the font; it sets the box width too.' },
    tester: { title: 'Tester', html: 'Words drawn by the live preview, unsaved changes included. Type your own, pick a <strong>Sample set…</strong> or <strong>Random</strong>; click a word to put it on the canvas. <strong>Build &amp; test</strong> opens the same words next to the built font.' }
  }
};

export const EDITOR_HELP: PanelHelp<EditorPanelId> = {
  section: 'editor',
  topics: {
    selection: { title: 'Selection', html: 'The position and size of what is selected: points (corner, smooth or free) or whole shapes (move, scale, rotate, centre in the box). With nothing selected it shows the glyph\'s shape count and its estimated stroke weight.' },
    compare: { title: 'Compare', html: 'Things to measure against while drawing: a <strong>reference dot</strong> (<kbd>D</kbd>) at the stroke weight to aim for, another glyph laid over this one (<kbd>G</kbd>), or the last saved outline (<kbd>L</kbd>).' },
    glyph: { title: 'Glyph', html: 'Which areas the glyph is in (and so its box size), and the file it saves to.' },
    typing: { title: 'Typing', html: 'The glyph\'s spellings: what you type to get it, in Latin letters, numbers and symbols, 简体 and 繁體. Two glyphs can\'t share a spelling. The same fields are in <a href="/glyphs?view=typing">Glyphs → Typing</a>.' },
    tryit: { title: 'Try it', html: 'Types each spelling on its own, and any word you enter, through the spellings as they are now, saved or not. Red means "not in the font" until the next build.' },
    checks: { title: 'Checks', html: 'Problems the build would trip on: an empty glyph, parts outside the box, open lines and specks, each with a button to fix it. <strong>Check as built</strong> runs the same conversion as the font build.' },
    tester: { title: 'Tester', html: 'Words that use this glyph, drawn live as you edit, so you can see it in context before saving.' },
    trace: { title: 'Trace', html: 'Turns the image you opened into an outline. Adjust <strong>Threshold</strong> (or <strong>Auto</strong>), specks, corners and simplify, then <strong>Use this outline</strong>. The image stays in your browser. <kbd>Esc</kbd> leaves trace mode.' }
  }
};
