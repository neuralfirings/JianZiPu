// CoreText shaping probe: prints glyph name and absolute position for each
// glyph of each word, at 1000pt (= font units for a 1000-UPEM font).
//   swift ctshape.swift FONT.ttf word1 word2 ...
import Foundation
import CoreText

let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
guard let provider = CGDataProvider(url: url as CFURL), let cg = CGFont(provider) else {
    print("cannot load font"); exit(1)
}
let features: [[CFString: Any]] = [
    [kCTFontOpenTypeFeatureTag: "liga", kCTFontOpenTypeFeatureValue: 1],
    [kCTFontOpenTypeFeatureTag: "kern", kCTFontOpenTypeFeatureValue: 1],
]
let base = CTFontCreateWithGraphicsFont(cg, 1000, nil, nil)
let desc = CTFontDescriptorCreateWithAttributes([kCTFontFeatureSettingsAttribute: features] as CFDictionary)
let font = CTFontCreateCopyWithAttributes(base, 1000, nil, desc)

for word in args.dropFirst(2) {
    let attr = NSAttributedString(string: word, attributes: [NSAttributedString.Key(kCTFontAttributeName as String): font])
    let line = CTLineCreateWithAttributedString(attr)
    let runs = CTLineGetGlyphRuns(line) as! [CTRun]
    var out: [String] = []
    for run in runs {
        let n = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: n)
        var pos = [CGPoint](repeating: .zero, count: n)
        CTRunGetGlyphs(run, CFRangeMake(0, 0), &glyphs)
        CTRunGetPositions(run, CFRangeMake(0, 0), &pos)
        let runFont = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName as String] as! CTFont
        let sameFont = CTFontCopyPostScriptName(runFont) as String == CTFontCopyPostScriptName(font) as String
        for i in 0..<n {
            let name = (cg.name(for: glyphs[i]) as String?) ?? "gid\(glyphs[i])"
            out.append("\(sameFont ? "" : "FALLBACK:")\(name):\(Int(pos[i].x.rounded())),\(Int(pos[i].y.rounded()))")
        }
    }
    print(word + "\t" + out.joined(separator: " "))
}
