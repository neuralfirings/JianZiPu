// Searching the glossary tables (Check the glossary): the rows whose ASCII, 中文, 拼音 or Meaning
// holds the search, or every row of a section whose title holds it. Tone marks, case and spaces
// don't count ("banfu" finds bàn fú); the last column (the examples) isn't searched, since nearly
// every example has 勾 in it. site/index.html's glossary searches the same way (its script).

/** Text as the search compares it: no tone marks, no spaces, lower case. */
export const norm = (t: string | null | undefined) =>
  (t ?? '').normalize('NFD').replace(/[̀-ͯ\s]/g, '').toLowerCase();

/** Does a row match: one of its searched cells, or its section's title, holds the search? */
export const rowMatches = (cells: string[], title: string, query: string) => {
  const q = norm(query);
  return !q || norm(title).includes(q) || cells.some((c) => norm(c).includes(q));
};

/** Hide the rows of `root`'s glossary tables that don't match, and a table (with its <h4> title)
 *  with none left; returns how many rows show. */
export function filterTables(root: HTMLElement, query: string): number {
  let shown = 0;
  for (const table of root.querySelectorAll('table')) {
    let title: Element | null = table.previousElementSibling;
    while (title && title.tagName !== 'H4' && title.tagName !== 'TABLE') title = title.previousElementSibling;
    const head = title?.tagName === 'H4' ? (title as HTMLElement) : null;
    let any = false;
    for (const tr of table.rows) {
      if (!tr.querySelector('td.gid')) continue;
      const cells = [...tr.cells].slice(1, -1).map((c) => c.textContent ?? '');
      const hit = rowMatches(cells, head?.textContent ?? '', query);
      tr.hidden = !hit;
      if (hit) { any = true; shown++; }
    }
    table.hidden = !any;
    if (head) head.hidden = !any;
  }
  return shown;
}
