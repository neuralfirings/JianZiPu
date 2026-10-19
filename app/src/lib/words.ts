// Sample word sets for the test strip and the Test & Build screen.
export const SAMPLE_SETS: Record<string, string[]> = {
  'Basic words': ['s7k5', 'd10u6', 'f9j3', 'v8h2', 'x5l1', 's76', '0k3', 'blk5', 'lun6', 'sanu1', 's7ju5', 's7ki5', 's7lo5'],
  Decimals: ['s7.5k5', 's7,5', '10.2', '13.9', '13+', '11.5', '7.5', '0.5', '1,3', 'fyd10.8ju6', 'U9,6', 's9U5,6'],
  Modifiers: ['s7.5>k5', '/u2', '\\k3', '>i4', 'fys9k5', 'fy>U5', 's7>\\k5', 'jiul7', 'banlunl7', 'diejuan', 'quanfu3', 'banfu2'],
  Chords: ['Cv9,6|03', 'C88|99', 'DCs7,5|02', 'TT3', 'BL5', 'BLv9\\6|05', 'Cs7>5|03', 'fyC88|99', 'C7|7'],
  Vertical: [':shang79', ':fenkai', ':banlun', ':大息', ':jiu', ':shang', ':xia', ':zhi4', ':v8', ':v8.5banlun7', ':shang51', ':jin'],
  'Chinese input': ['名七半急勾五', '名七五', '大九挑五', '中十点二抹一', '散挑三', '跪十一剔二', '食外勾一', '名九，半轮六', '泛音名七挑五', '大撮', '反撮', '抹挑', '打摘', '勾剔', '名十一二', '名十一', '名七徽六挑五', '名七点六挑五', '綽', '註', '歴', '雙彈', '撥剌'],
  'Edge cases': ['s7_5', '*', 's7k5 0k3', 's7k5+0k3', '#s7k5', 's7.5>k5 jiul7 0k3 s9,4 C88|99', 's7', '7\\5', 'fys7']
};
export const DEFAULT_STRIP = 's7k5 fys9k5 s7>\\k5 0k3 :shang79 Cv9,6|03';
