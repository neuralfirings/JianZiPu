// The Builder's icons, all from Lucide (lucide.dev), named by what they do so every screen uses
// the same drawing for the same job. Size and line weight come from routes/+layout.svelte
// (setLucideProps: 16px, 1.5px), square caps from app.css (.lucide-icon). To change an icon
// everywhere, change it here.

// header and editing
export { default as Undo } from '@lucide/svelte/icons/undo';
export { default as Redo } from '@lucide/svelte/icons/redo';
export { default as More } from '@lucide/svelte/icons/ellipsis';
export { default as Help } from '@lucide/svelte/icons/circle-question-mark';
export { default as Close } from '@lucide/svelte/icons/x';
export { default as Back } from '@lucide/svelte/icons/arrow-left';
export { default as Refresh } from '@lucide/svelte/icons/refresh-cw';
export { default as Gives } from '@lucide/svelte/icons/arrow-right';      // a rule row: glyph gives gap
export { default as Opens } from '@lucide/svelte/icons/arrow-up-right';   // a link to another screen
export { default as Plus } from '@lucide/svelte/icons/plus';
export { default as Minus } from '@lucide/svelte/icons/minus';
export { default as Preview } from '@lucide/svelte/icons/eye';

// panels, menus, disclosure
export { default as Grip } from '@lucide/svelte/icons/grip-vertical';
export { default as Folded } from '@lucide/svelte/icons/chevron-right';
export { default as Unfolded } from '@lucide/svelte/icons/chevron-down';
export { default as Dropdown } from '@lucide/svelte/icons/chevron-down';
export { default as Less } from '@lucide/svelte/icons/chevron-up';
export { default as Prev } from '@lucide/svelte/icons/chevron-left';
export { default as Next } from '@lucide/svelte/icons/chevron-right';

// status: always next to a word (design system: colour + icon + word)
export { default as Check } from '@lucide/svelte/icons/check';
export { default as Problem } from '@lucide/svelte/icons/x';
export { default as Warn } from '@lucide/svelte/icons/triangle-alert';
export { default as Alert } from '@lucide/svelte/icons/circle-alert';
export { default as Unsaved } from '@lucide/svelte/icons/circle-dot';
export { default as Working } from '@lucide/svelte/icons/loader-circle';
export { default as Info } from '@lucide/svelte/icons/info';
export { default as Draft } from '@lucide/svelte/icons/circle-dashed';
export { default as Current } from '@lucide/svelte/icons/circle-dot';     // the one in use: font, rule row
export { default as Lock } from '@lucide/svelte/icons/lock';               // held by a sent Change Request

// Change Requests
export { default as Send } from '@lucide/svelte/icons/send';
export { default as Withdraw } from '@lucide/svelte/icons/undo-2';

// layout rules
export { default as Vertical } from '@lucide/svelte/icons/move-vertical';
export { default as Horizontal } from '@lucide/svelte/icons/move-horizontal';
export { default as Otherwise } from '@lucide/svelte/icons/corner-down-right';
export { default as Required } from '@lucide/svelte/icons/asterisk';
export { default as Pair } from '@lucide/svelte/icons/arrow-left-right';   // a glyph and its vertical form
export { default as PartnerOf } from '@lucide/svelte/icons/corner-left-up';

// glyph editor
export { default as ToolSelect } from '@lucide/svelte/icons/mouse-pointer-2';
export { default as ToolPen } from '@lucide/svelte/icons/pen-tool';
export { default as ToolPencil } from '@lucide/svelte/icons/pencil';
export { default as ToolRect } from '@lucide/svelte/icons/square';
export { default as ToolEllipse } from '@lucide/svelte/icons/circle';
export { default as ToolHand } from '@lucide/svelte/icons/hand';
export { default as ToolZoom } from '@lucide/svelte/icons/zoom-in';
export { default as Grid } from '@lucide/svelte/icons/grid-3x3';
export { default as Shortcuts } from '@lucide/svelte/icons/keyboard';
export { default as Union } from '@lucide/svelte/icons/squares-unite';
export { default as Subtract } from '@lucide/svelte/icons/squares-subtract';
export { default as Intersect } from '@lucide/svelte/icons/squares-intersect';
export { default as Exclude } from '@lucide/svelte/icons/squares-exclude';
export { default as FlipH } from '@lucide/svelte/icons/triangles-centerline-dashed-vertical';   // mirror across a vertical line
export { default as FlipV } from '@lucide/svelte/icons/triangles-centerline-dashed-horizontal';
