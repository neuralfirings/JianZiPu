# Changelog

Every released version of the JianZiPu font, newest first, in the style of
[Keep a Changelog](https://keepachangelog.com/): each version lists what was Added,
Changed, Fixed or Removed. Version numbers have a three-digit minor part (3.100,
3.200, 3.201) because the font stores its version as a number; the major number
goes up only when existing documents would look different or break. A release's
entry is written by the Release screen (builder/README.md "Releases"), and the
same text becomes the GitHub release notes.

## [Unreleased]

### Added
- A word with a character only a vertical word can hold (上, 下, 分开…) is set vertically without typing the colon: `shang34` gives the same as `:shang34`.

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