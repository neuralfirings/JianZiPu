// The Chinese fonts after JianZiPu, the same order as the public font page (site/index.html):
// TW-Kai, the font JianZiPu's characters come from, served by emfont as "CNSKai" (the browser
// fetches only the pieces for characters on screen), then LXGW WenKai TC from Google Fonts.
// Their stylesheets are large lists of pieces, so they're added once the app is up rather than
// in app.html, where they would hold up the first paint; until then (and offline) Chinese shows
// in the system fonts at the end of --font-cjk in app.css. Both hosts are in the CSP (svelte.config.js).
export const CNSKAI_CSS = 'https://font.emtech.cc/css/CNSKai/400';
export const WENKAI_CSS = 'https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC:wght@400;700&display=swap';

// TW-Kai draws its characters smaller in the em than most Chinese fonts (about 0.83 em tall against
// LXGW WenKai TC's 0.90), so they looked small beside the Latin text. Every one of emfont's pieces
// gets this size-adjust, which scales CNSKai alone wherever it's used. The font page uses the same value.
export const CNSKAI_SIZE = '130%';

/** emfont's stylesheet with size-adjust added to each @font-face. */
export const withSizeAdjust = (css: string, size = CNSKAI_SIZE) => css.replace(/@font-face\s*\{/g, `@font-face { size-adjust: ${size};`);

function addLink(href: string) {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = href;
  document.head.append(link);
}

let started = false;
export function loadWebfonts() {
  if (started) return;
  started = true;
  addLink(WENKAI_CSS);
  // emfont allows the stylesheet to be read (CORS), so it goes in as a <style> with size-adjust;
  // if that fetch fails, the plain stylesheet still gives TW-Kai, only at its own size
  fetch(CNSKAI_CSS)
    .then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
    .then((css) => {
      const style = document.createElement('style');
      style.dataset.webfont = 'CNSKai';
      style.textContent = withSizeAdjust(css);
      document.head.append(style);
    })
    .catch(() => addLink(CNSKAI_CSS));
}
