# JianZiPu Font

JianZiPu is a way to write notation for Guqin (古琴) music. This document will cover how to use this font, and how to contribute to its design. 

Demo & Documentation: https://neuralfirings.github.io/jianzipu/

The rest of this document goes into the font compiling, and font input compiler. 

## Usage on Websites / JavaScript Packages

```
<script type="module">
	import { convert, getCharacter } from './dist/jianzipu.js'
	convert("s7ju5")
	convert("s7ju5 :shang,6,7 #jin")
	getCharacter("s6ju5")
</script>
```

To use the Javascript: 
* `convert(string)` -- converts the string of multiple characters to JianZiPu unicodes. A "character" is usually composed of multiple unicode glyphs, they will probably show up in most font as a box. When rendered with the JianZiPu.otf font, it'll show up as JianZiPu. You use spaces to separate characters. 
* `getCharacter(string)` -- converts one character at a time.

To render JianZiPu on your website:

* `jzp` class: anything embedded in `[[double brackets]]` will be in JianZiPu string using the JZP font; anything in `[[[triple brackets]]]` will be converted to a JianZiPu charater using the JZP font
* `jzp-font` class: anything here will use the JianZiPu font

## Usage as a Font

To use the font, install `/dist/JianZiPu.otf` file. You will still need a compiler since the font itself uses unicodes in the 58000 range (per its html entity).

You can access the compiler here: https://neuralfirings.github.io/jianzipu/ 

You type in the string (e.g., `3ks(7)`), and then copy/paste the compiled characters into whatever you want (I've tested with Microsoft Word), and make sure it's rendered using the JianZiPu.otf font (see .otf in the dist folder.)

## Technical Documentation: How the Font is Made

This is the part where we go into the nitty gritty of how this font works, and how you can contribute in this project. 

**1. The Art** 

[Figma](https://www.figma.com/design/CC89RmepV34CVP9bKWu48b/JianZiPuComponents-(v2)?node-id=0-925&t=nnXDKFURenKOGjYz-1) -- this contains the actual character and character component art. 

* Glyph/Area Components: This page has the individual components that make up the font. The glyphs here export to SVGs which goes into compiling the font.
* Layouts: This page has a series of layouts. Each layout is composed of a set of areas arranged in slightly differnet ways. Each area can include glyphs. The layout used is selected using the JavaScript IME. 

**2. Area/Key Map & Translator**

* `src/areaKeySVGMap.csv` contains which glyphs map to which areas, also contains which key triggers that glyph to render. 
* `src/keyTranslation.csv` contains how to translate certain letters or characters to the key that's used. 

One todo is combining these two into one file. 

**3. Compiler (Javascript)**

* `src/jianzipu.js` contains the compiling instructions. Basically it parses a string ":shang,7 #fu4 s7k5 名7勾5 (etc)" and converts it into the right unicodes. It does this by figuring out which layout to use, then which glyphs to use given those layouts. 


## Font Compiling Instructions

1. Figma: Export Glyphs to SVG
	* Figma > Glyphs Page
	* Copy glyph symbols, paste into new page 
	* Highlight all Symbols
		* Detach (cmd + opt + B)
		* Outline Stroke (Opt + Cmd + O)
		* (note: ensure fill is unchecked as part of export )
		* Left panel > search for "slice"
		* Copy all and export as SVG
	* rename exported files and remove "_slice" (ex: foo_slice.svg >> foo.svg)
2. Figma: Export Area Definitions to TXT
	* Figma > Layouts
	* Select what you want to export > Copy/Paste as > Copy as code > CSS (all layers)
	* Paste in `/src/figmaAreaDefinitions.txt`
	* `node ./src/scripts.cjs --compile --write`
3. CSV: Map characters to areas
	* Open charMap.csv
	* Add characters for each area
	* `node ./src/scripts.cjs --compile --write`
4. FontForge: Create the font
	* Open `/src/JianZiPu.blank.sfd` in FontForge, save as new version (ex: JianZiPu.sfd) (also update the font version Edit > Font Info)
	* Modify `/src/fontForgeScript.py` > set HOME_PATH and FILE_NAME
	* Copy script from fontForgeScript.py
	* In FontForge, open Python console (Cmd + .) > paste in fontForgeScript.py > run
	* Generate Font > select Open Type, save as .otf file (make sure Options > Open Type is checked)
5. Layout rules
	* Modify `/src/jianzipu.js` file if rules need to be modified
6. Key Translations
	* Modify `src/keyTranslations.csv` if translation rules need to be modified/added
	* Can use https://tableconvert.com/excel-to-json to convert this to JSON for babel.json (TODO: script this later)
7. Test with `src/index.html`
8. Build with `parcel build`

## Credits/License

Code is licensed under [The MIT License](https://opensource.org/licenses/MIT). 

Font is licensed under [Open Font License](https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL).

Font is adapted from the beautiful [Ma Shan Zheng](https://fonts.google.com/specimen/Ma+Shan+Zheng) font.