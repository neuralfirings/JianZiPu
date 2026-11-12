// Which glyph the Rename box is open for (one box for the whole app, in routes/+layout.svelte).
// Opened from the glyph editor's name, the Glyphs panel's name and List view's Glyph Name cell.
// `done` / `undone`: what the screen does after the rename, and after its Undo (go to the new
// name's page and back, or select the new name and back).
class Renaming {
  name = $state<string | null>(null);
  done: ((from: string, to: string) => void) | undefined;
  undone: ((from: string, to: string) => void) | undefined;
  ask(name: string, o: { done?: (from: string, to: string) => void; undone?: (from: string, to: string) => void } = {}) {
    this.done = o.done;
    this.undone = o.undone;
    this.name = name;
  }
  close() { this.name = null; }
}
export const renaming = new Renaming();
