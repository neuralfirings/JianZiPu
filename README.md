# JianZiPu Font

JianZiPu is a way to write notation for Guqin (古琴) music. This document will cover how to use this font, and how to contribute to its design. 

Demo: https://neuralfirings.github.io/jianzipu/

![](demo/screenshotCompiler.png)


## Guqin Shorthand for JianZiPu entry

The core of this font is a series of components (think, letters in word) that overlaps to form characters. These letters are represented by unicode characters. To determine which unicode characters to use, we will need to compile a shorthand developed for this font. The compiler looks at:

* **Strings**: represented by numbers outside of parentheses.
* **Hui position**: represented by numbers inside parentheses, since huis are round and parentheses are round, like `(7)` or `(6.7)`. Use `(0)` for open string.
* **Left hand positions**: represented by the following: `s,d,f,v` since that's where the left hand fingers are on a (US-based) keyboard
* **Right hand positions**: reprented by: `njkl` for plucks towards the player, `huio` away from the player
* **Chords (cuo)**: representedy by `H` (cuo), `U` (fan cuo), `I` (da cuo), `O` (da+fan cuo). 
* **Li**: represented by `U` 

So a string like `6ks(9)` would produce a character that represents...

* `6` -- 6th string
* `k` -- gou (pluck inward with the right middle finger)
* `s` -- press the string with left hand 4th finger on...
* `(9)` -- hui position 9

![](demo/6ks(9).character.png)

Now, if you just type this in the font you'll get a string of components, not the actual characters. To produce the actual character, you'll need a special compiler. It just so happens, I have included one in this package in the form of a webpage. If you clone this package and open the `index.html` file, you should get a text area for inputting the shorthand. 

You can also find this compiler here: https://neuralfirings.github.io/jianzipu/

## Usage on Websites

If you want to embed JianZiPu in your website, you can copy/paste the three files in the `/dist` folder and include them in your header. 

```
<script src="/path/to/jianzipu.js"></script>
<link rel="stylesheet" href="/path/to/jianzipu.css">
```

Or, you can use the GitHub.io as CDN. 


```
<script src="https://neuralfirings.github.io/jianzipu/dist/jianzipu.js"></script>
<link rel="stylesheet" href="https://neuralfirings.github.io/jianzipu/dist/jianzipu.css">
```

To render JianZiPu on your website:

* `jzp` class: anything embedded in `[[double brackets]]` will be in JianZiPu string using the JZP font; anything in `[[[triple brackets]]]` will be converted to a JianZiPu charater using the JZP font
* `jzp-font` class: anything here will be use the JianZiPu font

**Example of a String:**

![](demo/6ks(9).string.png)
```
<div class="jzp">[[6ks(9)]]</div>
```

**Example of a Character:**

![](demo/6ks(9).character.png)
```
<div class="jzp">[[[6ks(9)]]]</div>
```

**Example of Using the Raw Font:**

![](demo/6ks(9).character.png)

```
<div class="jzp-font" style="font-size: 5rem">&#58101;&#58090;&#58053;&#58063;</div>
```

## Usage as a Font

To use the font, install `/dist/JianZiPu.otf` file. You will still need a converter since the font itself uses unicodes in the 58000 range (per its html entity)

You can access the converter here: https://neuralfirings.github.io/jianzipu/ 

You type in the string (e.g., `3ks(7)`), and then copy/paste the compiled characters. 

You can also use the unicodes themselves, but this might get a bit unweildy. 

## Font Mechanics

This is the part where we go into the nitty gritty of how this font works, and how you can contribute in this project. 

There are three main components to the font. 

### 1. Character component graphics SVGs

These are the raw graphics (SVGs) that make up individual components in a JianZiPu character. These are stored in the `/components` folder. I use `/font/JianZiPuComponents.sketch` to organize my workspace and generate SVGf files in bulk. 

### 2. Character map (`charMap`) JSON

This represents a "map" of how various components can be laid out in the character. The map is a JSON object with different areas. Each area has:

* *x*: x coordinate of where the area starts relative to the top/left corner of the character
* *y*: y coordinate of where the area starts relative to the top/left corner of the character
* *w*: the width of the area
* *h*: the height of the area
* *components*: an array of components that can go into the area. Each component is an object with...
	* *key*: this represents what the compiler looks up. For example, the key `1` represents a component representing 1. The key `k` represents a gou component. 
	* *filename*: this is the filename (SVG) for the component
	* *unicode*: this is the unicode to assign to the component
	* *width*: this is the width of the component. Most components have 0 as width, so the componenets can layer and stack on top of one another. 
	* *scale* (optional): this is how we want to scale the component to fit its area. By default, it will scale horizontally and vertically to fit the area. There's also the option of using `lockRatio` so the component's ratio remains the same. 

This map is present in `/dist/jianzipu.js` and `/font/fontForgeScript.py`.

### 3. Character rules (`charRules`) JSON

This map represents the rules used to compile the font from shorthand. It's a series of RegEx expressions which matches a particular string (e.g., if a hui position exists), and assigns which areas to the matching string. 

The compiler then executes the areas in order. For example `{ regex: /[0-9]/, area: 'strFull'}` is the first rule, which looks for the existance of numbers to assign it to the `strFull` area. Later rules will assign any numbers as areas specific to huis (if parentheses exists) or smaller areas in the component if things like left hand keys exists. 

### Font Compiling Instructions

These are the steps I use. 

1. Edit components
	* Open `/src/JianZiPuComponents.sketch`: select all / export as SVG (transparent background)
2. Modify `/src/charMap.js` file
	* Make sure unicodes are unique and something in the 58000 range
	* To do this in Sublime (with Text Pastry plugin): highlight `"unicode": ` > Ctrl+Cmd+G to select all > Scroll over to the unicodes and replace with > Package: Text Pastry Command Line, `\i(58000,1)`
3. Modify `/src/charRules.js` file if rules need to be modified. Get comfy with RegEx.
4. Create the font
	* Open JianZiPu.blank.sfd, save as new version (ex: JianZiPu.sfd) (also update the font version Edit > Font Info)
	* Modify `/src/fontForgeScript.py` > HOME_PATH so that it's pointing to the JianZiPu directory
	* Open Python console (Ctrl + .) > copy/paste in fontForgeScript.py > run
	* Generate Font > select Open Type, save as .otf file (make sure Options > Open Type is checked)
5. Compile Javascript, while in JianZiPu directory..
	* run `uglifyjs ./src/*.js -o ./dist/jianzipu.min.js` or something similar
	* run `cp ./dev/JianZiPu.otf ./dist/JianZiPu.otf`

## Example of Shorthand

**梧叶舞秋风**

Here are the first few lines of my favorite Guqin piece to play, 梧叶舞秋风.

```
3fk(7) 4k 6vu(7) 3sk(9) 6vk(7) f(7)U7,6 5k 6vu(7) 3fk(7) 7vu(7) 6u 3s(9)k  
6vu(7) 3fk(7) 4k 5juv(7) 3fk(7) 5vu(7) 5juf(7) 3kf(7) 5vu(7) 4u 1kd(9)
4vk(7) 6vu(7) 3sk(9) 6vu(7) 4,3Uv(7) 4,3Uv(7) 2fk(7) 4vu(7) 3k 4sk(7.6)
7juv(6.2) \7jv(7) \7u sc(7.6) 6us(10.9) 
6V(7) 4kf(7) 5uv(7) 4uv(7.6) 2fk(7.6) \3v(7.9)k 4vk(7.6) 5u? sc(8.5) 3k(0) 5v(8.5)u 
4v(9)k 5v(8.5)u 4uv(9) sc(10) 3sk(10.8) 4vu(10) 2kf(10)? 3sk(10.8)
```

This generates

![](demo/leavesExample.png)

## To Do 

Should probably move this to use the Issues tracker in Github.

- slides in cuo
- Shuang1 Tan3 (in the Leaves)
- insert random text in vertical order
- Fix styling in the hui decimal

## Credits/License

Code is licensed under [The MIT License](https://opensource.org/licenses/MIT). 

Font is licensed under [Open Font License](https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL).

Font is adapted from the beautiful [Ma Shan Zheng](https://fonts.google.com/specimen/Ma+Shan+Zheng) font.