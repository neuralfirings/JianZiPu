// Raster to outline: threshold the image to black and white, trace it with
// potrace (WASM), and hand back SVG path data in image pixels.
import { init, potrace } from 'esm-potrace-wasm';

export type TraceOptions = {
  threshold: number;   // 0–255: pixels darker than this are ink
  invert: boolean;     // trace light-on-dark images
  despeckle: number;   // potrace turdsize: drop blobs smaller than this many pixels
  smoothing: number;   // potrace alphamax 0–1.34: corner threshold (higher = rounder)
  tolerance: number;   // potrace opttolerance: curve optimisation (higher = fewer nodes)
};

export const TRACE_DEFAULTS: TraceOptions = { threshold: 128, invert: false, despeckle: 4, smoothing: 1, tolerance: 0.3 };

let ready: Promise<void> | null = null;

/** Draw the image to a canvas, thresholded to pure black on white. */
export function thresholdImage(img: HTMLImageElement | ImageBitmap, o: TraceOptions, maxSide = 1200): HTMLCanvasElement {
  const s = Math.min(1, maxSide / Math.max(img.width, img.height));
  const w = Math.max(1, Math.round(img.width * s)), h = Math.max(1, Math.round(img.height * s));
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const ctx = c.getContext('2d', { willReadFrequently: true })!;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
  ctx.drawImage(img, 0, 0, w, h);
  const d = ctx.getImageData(0, 0, w, h);
  const px = d.data;
  for (let i = 0; i < px.length; i += 4) {
    const a = px[i + 3] / 255;
    const lum = (0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]) * a + 255 * (1 - a);
    let ink = lum < o.threshold;
    if (o.invert) ink = !ink;
    const v = ink ? 0 : 255;
    px[i] = px[i + 1] = px[i + 2] = v; px[i + 3] = 255;
  }
  ctx.putImageData(d, 0, 0);
  return c;
}

/** Trace a thresholded canvas. Returns an SVG document (viewBox = image pixels). */
export async function traceCanvas(c: HTMLCanvasElement, o: TraceOptions): Promise<string> {
  ready ??= init();
  await ready;
  const svg = await potrace(c, {
    turdsize: Math.max(0, Math.round(o.despeckle)), alphamax: o.smoothing, opticurve: 1, opttolerance: o.tolerance,
    turnpolicy: 4, pathonly: false, extractcolors: false, posterizelevel: 1
  });
  return svg;
}

export function loadImage(file: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('not an image the browser can read')); };
    img.src = url;
  });
}
