import { describe, expect, it } from 'vitest';
import { filterTables, norm, rowMatches } from './glossarySearch';

const row = (id: number, cells: string[]) =>
  `<tr id="${id}"><td class="gid"><a href="#${id}">${id}</a></td>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`;
const table = (rows: string) => `<table><thead><tr><th>ID</th><th>ASCII</th></tr></thead>${rows}</table>`;

describe('glossary search', () => {
  it('ignores tone marks, case and spaces', () => {
    expect(norm('Bàn Fú')).toBe('banfu');
    expect(rowMatches(['bf', '半扶', 'bàn fú', '<jzp>'], '', 'ban fu')).toBe(true);
    expect(rowMatches(['k', '勾', 'gōu'], '', 'GOU')).toBe(true);
    expect(rowMatches(['k', '勾', 'gōu'], '', 'tiao')).toBe(false);
    expect(rowMatches(['C', '撮', 'cuō'], '2b: Chords', 'chords')).toBe(true);   // the section's title
    expect(rowMatches(['k'], '', '  ')).toBe(true);                              // no search: everything
  });
  it('hides rows, and a section with none left, but never searches the examples', () => {
    const root = document.createElement('div');
    root.innerHTML = '<h4>1a: Left Hand Finger</h4>' + table(row(1, ['s', '名', 'míng', '名九勾三']) + row(2, ['d', '中', 'zhōng', '中九勾三']))
      + '<h4>2a: Basic Right Hand</h4>' + table(row(3, ['k', '勾', 'gōu', '散勾五']));
    const [h1, h2] = root.querySelectorAll('h4');
    const [t1, t2] = root.querySelectorAll('table');
    expect(filterTables(root, '勾')).toBe(1);                 // 名九勾三 is an example, not the row's own
    expect([h1.hidden, t1.hidden, h2.hidden, t2.hidden]).toEqual([true, true, false, false]);
    expect(filterTables(root, 'zhong')).toBe(1);
    expect([...t1.rows].map((r) => r.hidden)).toEqual([false, true, false]);   // the header row stays
    expect(filterTables(root, 'left hand')).toBe(2);
    expect(filterTables(root, '')).toBe(3);
    expect(root.querySelectorAll('[hidden]').length).toBe(0);
  });
});
