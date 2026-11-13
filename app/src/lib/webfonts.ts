// The Chinese fonts after JianZiPu, the same order as the public font page (site/index.html):
// TW-Kai, the font JianZiPu's characters come from, served by emfont as "CNSKai" (the browser
// fetches only the pieces for characters on screen), then LXGW WenKai TC from Google Fonts.
// Their stylesheets are large lists of pieces, so they're added once the app is up rather than
// in app.html, where they would hold up the first paint; until then (and offline) Chinese shows
// in the system fonts at the end of --font-cjk in app.css. Both hosts are in the CSP (svelte.config.js).
export const WEBFONT_CSS = [
  'https://font.emtech.cc/css/CNSKai/400',
  'https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC:wght@400;700&display=swap'
];

export function loadWebfonts() {
  for (const href of WEBFONT_CSS) {
    if (document.querySelector(`link[href="${href}"]`)) continue;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.append(link);
  }
}
