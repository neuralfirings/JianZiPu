# Changelog

Every released version of the JianZiPu font, newest first, in the style of
[Keep a Changelog](https://keepachangelog.com/): each version lists what was Added,
Changed, Fixed or Removed. Version numbers have a three-digit minor part (3.100,
3.200, 3.201) because the font stores its version as a number; the major number
goes up only when existing documents would look different or break. A release's
entry is written by the Release screen (builder/README.md "Releases"), and the
same text becomes the GitHub release notes.

## [Unreleased]

## [3.301] - 2026-11-13

### Fixed

- On iPhone and in Safari, a vertical word (`shang34`, `:xia79`…) followed by a space no longer leaves an extra character's width of space after it. A colon typed straight after a word with no space (`s9k3:shang34`) now makes room for that word instead of drawing over it, and so does `#` after a vertical word. A vertical word with nothing after it now takes no width of its own, like every other word.

## [3.300] - 2026-11-13

### Added
- New characters, with their spellings: 从 `cong`, 头 `tou`, 再 `zai`, 作 `zuo`, 【 `[`, 曲 `qu`, 终 (終) `zhong`, 又 `you`, 推出 `tc` / `tuichu`, 游吟 `youyin`. Together they write 从头再作, 从【再作 and 曲终.
- 大 (thumb) can also be typed `da`, as well as `v`.
- A word with a character only a vertical word can hold (上, 下, 分开…) is set vertically without typing the colon: `shang34` gives the same as `:shang34`.
- Spellings can use `[` and `]` (Latin) and Chinese punctuation such as 【 】 《 》 (简体/繁體). `[` and 【 now both type the new 【 mark; 】 typed in Chinese still becomes `]`.

### Changed
- The glossary on jianzipufont.com is reorganised: numbered sections (1.1, 1.2…), a new "Numbers for String and Hui" section, a Definition column, and more example words. Rows are renumbered and some section links changed (#glossary-1d, #glossary-3c and others are gone), so old links to a row or section may land somewhere else.
- The license no longer reserves the name "JianZiPu": the font's copyright line and OFL.txt drop "with Reserved Font Name". A changed copy of the font may keep the name.

### Fixed
- Typing a word letter by letter in Chrome or Edge no longer leaves it half-built (`daiqi` set horizontally, `fenkai` or `zhua` in pieces) until the text is pasted again. Words starting with two letters drawn at the same width, such as `shang`, `ban` or `duan`, can still go wrong while typing in Chrome 153; pasted text is right.

## [3.200] - 2026-10-21

### Changed
by Nancy Liang
- Add rules for string top/bottom for non li right hand characters
- Fixed spacing issue with chords 
- Change advance of chord | to 500 
- add 8 and 9 string for 9 string guqin use case

## [3.100] - 2026-10-19

The v3.1 font (tag `v3.1`), renumbered: from here on the version is 3.100.

### Added
- added 歴 to the font as traditional version of 历
- added support for 9 string qin
- added 弦 as a character to the font, but this isn't incorporated into the code yet. Will need to incorporate this to be used as a string indicator in a later version.

## [3.0]

This version got rid of the compiler, and embedded all the logic into the font. So you can just install the font and it should work in any software. So far, I've tested with MuseScore 4.3 (note: doesn't work in versions after this for some reason), Sibelius, Word, Chrome, and Safari.

## [2]

This version was created using the TW-Kai font as a base. It looked so much better. It used JavaScript to pick which glyphs to use in a "word" so it relied on a compiler. 

You had to entire in text through a compiler, then copy/paste the unicodes into a document that had the font installed. 

Demo here: https://guqintabs.com/jianzipu/v2/

## [1]

This version was created using the Ma Shan Zheng font as a base. The balance of the glyphs left lot to be desiered. 

The code worked, but it didn't look great. 

Also, the nomenclature didn't really follow how a JZP character is "read" aloud. 

Demo here: https://guqintabs.com/jianzipu/v1/