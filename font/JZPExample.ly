% v9
lm = #(define-music-function (note) (ly:music?) #{  \override NoteHead.style = #'cross $note \revert NoteHead.style #} )
fy = #(define-music-function (pos note) ((number? 1) ly:music?) (let ( (stringNum (ly:prob-property (list-ref (ly:music-property note 'articulations) 0) 'string-number)) (tuning  (list #{c\0#} #{g,,\1#} #{a,,\2#} #{c,\3#} #{d,\4#} #{e,\5#} #{g,\6#} #{a,\7#} )) ) (let ( (base (list-ref tuning stringNum)) ) (define noteP (ly:music-property note 'pitch)) (define baseP (ly:music-property base 'pitch)) (define intNote (ly:pitch-diff (ly:music-property base 'pitch) (ly:music-property note 'pitch) )) (define interval (ly:pitch-tones (ly:pitch-diff (ly:music-property note 'pitch) (ly:music-property base 'pitch)))) (cond ( (= interval 6 ) #{ \transpose c f, { \harmonicByFret #7 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 9.5 ) (= pos 5)) #{ \transpose c g, { \harmonicByFret #5 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 9.5 ) (= pos 9)) #{ \transpose c ees, { \harmonicByFret #9 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 9.5 ) (= pos 1)) #{ \transpose c g, { \harmonicByFret #5 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 12 ) (= pos 4)) #{ \transpose c aes, { \harmonicByFret #4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 12 ) (= pos 10)) #{ \transpose c c'' { \harmonicByFret #10 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 12 ) (= pos 1)) #{ \transpose c aes, { \harmonicByFret #4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 14 ) (= pos 3)) #{ \transpose c a, { \harmonicByFret #3 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 14 ) (= pos 6)) #{ \transpose c e'' { \harmonicByFret #6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 14 ) (= pos 8)) #{ \transpose c e'' { \harmonicByFret #8 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 14 ) (= pos 11)) #{ \transpose c e'' { \harmonicByFret #11 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 14 ) (= pos 1)) #{ \transpose c e'' { \harmonicByFret #6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 15.5 ) (= pos 2)) #{ \transpose c f, { \harmonicByFret #2 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 15.5 ) (= pos 12)) #{ \transpose c g' { \harmonicByFret #12 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 15.5 ) (= pos 1)) #{ \transpose c f, { \harmonicByFret #2 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 1.4)) #{ \transpose c bes'' { \harmonicByFret #1.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 4.4)) #{ \transpose c bes'' { \harmonicByFret #4.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 6.3)) #{ \transpose c bes'' { \harmonicByFret #6.3 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 7.7)) #{ \transpose c bes'' { \harmonicByFret #7.7 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 9.6)) #{ \transpose c bes'' { \harmonicByFret #9.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 12.6)) #{ \transpose c bes'' { \harmonicByFret #12.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 17 ) (= pos 1)) #{ \transpose c bes'' { \harmonicByFret #6.3 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 18 ) (= pos 1)) #{ \transpose c c''' { \harmonicByFret #1 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 18 ) (= pos 5.6)) #{ \transpose c c''' { \harmonicByFret #5.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 18 ) (= pos 8.4)) #{ \transpose c c''' { \harmonicByFret #8.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 18 ) (= pos 13)) #{ \transpose c c''' { \harmonicByFret #13 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 0.9)) #{ \transpose c d''' { \harmonicByFret #0.9 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 3.4)) #{ \transpose c d''' { \harmonicByFret #3.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 6.4)) #{ \transpose c d''' { \harmonicByFret #6.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 7.6)) #{ \transpose c d''' { \harmonicByFret #7.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 10.6)) #{ \transpose c d''' { \harmonicByFret #10.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 13.1)) #{ \transpose c d''' { \harmonicByFret #13.1 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 19 ) (= pos 1)) #{ \transpose c d''' { \harmonicByFret #6.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 20 ) (= pos 0.8)) #{ \transpose c e''' { \harmonicByFret #0.8 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 20 ) (= pos 4.6)) #{ \transpose c e''' { \harmonicByFret #4.6 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 20 ) (= pos 9.4)) #{ \transpose c e''' { \harmonicByFret #9.4 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 20 ) (= pos 13.2)) #{ \transpose c e''' { \harmonicByFret #13.2 $(ly:music-transpose note intNote) } #} ) ( (and (= interval 20 ) (= pos 1)) #{ \transpose c e''' { \harmonicByFret #4.6 $(ly:music-transpose note intNote) } #} ) ( else #{ $note #} ) ) ) ) )
tuning = <a, g, e, d, c, a,, g,,>
#(ly:font-config-add-font "/Users/nyl/git_projects/JianZiPu/dist/JianZiPu.otf")

#(set-default-paper-size "letter") \header {
  title = \markup \center-column {"Test JZP" " " }
  tagline = "guqin.nyl.io"
  poet = \markup \column {"Tuning: G,, A,, C, D, E, G, A, " " "}
}
\paper {
  #(include-special-characters)
}

voice_default = {
  \clef "bass"
  \set Score.barNumberVisibility = #all-bar-numbers-visible
  \tempo 4=78
  \time 2/4
  a,8\5^"3v"_"4" a,,\2^"v" c\5^"2^"_"1" ( b,\5 ) \set Score.currentBarNumber = #2 \bar "|" a,4\5_"4" a,,\2^"3v" \set Score.currentBarNumber = #3 \bar "|" a,8\5^"2^"_"4" a,,\2^"3v" e\7^"2^"_"1" d\6 \set Score.currentBarNumber = #4 \bar "|" e4\6^"^"_"/1" <a,,\2e,\5>^"2^"^"3v" \set Score.currentBarNumber = #5 \bar "|" 

}
 
jzp = \lyricmode {

  "щрЬϾІ " "ЪРϾЏК " j k
}

tuningEqual = #'("0" "13.6"  "13.1"  "12.2"  "10.9"  "10"  "9.5"  "9"  "8.4"  "7.9"  "7.6"  "7.3"  "7"  "6.7"  "6.5"  "6.2"  "6"  "5.6"  "5.3"  "5"  "4.8"  "4.6"  "4.4"  "4.2"  "4"  "3.7"  "3.5"  "3.2"  "3"  "2.6"  "2.3"  "2"  "1.8"  "1.6"  "1.4"  "1.2"  "1")
tuningJust = #'("0" "13.6" "13.1" "12.2" "11" "10" "9.5" "9" "8.5" "8" "7.7" "7.3" "7" "6.7" "6.4" "6.2" "6" "5.6" "5.3" "5" "4.8" "4.6" "4.4" "4.2" "4" "3.7" "3.4" "3.2" "3" "2.6" "2.3" "2" "1.8" "1.6" "1.4" "1.2" "1")

\score {
  \layout { 
    \context { \TabStaff stringTunings = \stringTuning \tuning fretLabels = \tuningEqual }
    \context { \Lyrics \override LyricText.font-name = "JianZiPu"}
    \context { \Lyrics \override LyricText.font-size = #5 }
    \context { \Score automaticBars = ##f }
    \context { \Score \override RehearsalMark.self-alignment-X = #LEFT \override RehearsalMark.font-size = #-1 } 
    \context { \Staff \hide TextScript \override TrillSpanner.bound-details.left.text = ##f \override Glissando.style = #'zigzag }
    \context { \TabStaff \omit Clef \omit ClefModifier \revert TextScript.stencil \override TextScript.font-size = #-3 \override Glissando.style = #'zigzag \override TabNoteHead.font-family = #'typewriter tablatureFormat = #fret-letter-tablature-format } 
    \textLengthOn \omit Voice.StringNumber 
  } 
  \midi {}
  <<  \new Voice = "forjzp" { \voice_default }  \new Lyrics \lyricsto "forjzp" { \set ignoreMelismata = ##t \jzp } \new TabStaff  { \clef "moderntab" <<  \voice_default >> } >>
}
