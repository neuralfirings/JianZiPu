// The help page's contents list: one entry per section of routes/help/+page.svelte,
// in page order. help.test.ts checks every id has its section and every link lands.
export const HELP_SECTIONS: { id: string; title: string }[] = [
  { id: 'start', title: 'Getting started' },
  { id: 'typing', title: 'How words are typed' },
  { id: 'glyphs', title: 'Glyphs' },
  { id: 'editor', title: 'The glyph editor' },
  { id: 'layouts', title: 'Layouts' },
  { id: 'build', title: 'Build & test' },
  { id: 'saving', title: 'Saving and undo' },
  { id: 'draft', title: 'Your draft (online)' },
  { id: 'review', title: 'Reviewing a draft' },
  { id: 'keys', title: 'Keyboard shortcuts' },
  { id: 'trouble', title: 'When something looks wrong' }
];
