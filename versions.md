# Versions

## v3.1
- added 歴 to the font as traditional version of 历
- added support for 9 string qin
- added 弦 as a character to the font, but this isn't incorporated into the code yet. Will need to incorporate this to be used as a string indicator in a later version.

## v3.0
This version got rid of the compiler, and embedded all the logic into the font. So you can just install the font and it should work in any software. So far, I've tested with MuseScore 4.3 (note: doesn't work in versions after this for some reason), Sibelius, Word, Chrome, and Safari.

## v2
This version was created using the TW-Kai font as a base. It looked so much better. It used JavaScript to pick which glyphs to use in a "word" so it relied on a compiler. 

You had to entire in text through a compiler, then copy/paste the unicodes into a document that had the font installed. 

Demo here: https://guqintabs.com/jianzipu/v2/

## v1
This version was created using the Ma Shan Zheng font as a base. The balance of the glyphs left lot to be desiered. 

The code worked, but it didn't look great. 

Also, the nomenclature didn't really follow how a JZP character is "read" aloud. 

Demo here: https://guqintabs.com/jianzipu/v1/