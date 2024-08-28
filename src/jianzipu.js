import charMap from './charMap.json'
import babelDict from './babel.json'
import babelfish from './babelDict.json'
if (typeof window !== 'undefined') {
  import('./jianzipu.css');
}

const babel = _sortArrayByKeyDesc(babelDict, "key")
const plucks = babel.filter(e => e.leftVsRightSeparator == "yes").map(e => e.key)
const leftHandPositions = babel.filter(e => e.category == "left").map(e => e.key)
const chords = babel.filter(e => e.category == "chord").map(e => e.key)

// const CHORD_KEYS = ["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"]
// const HUI_PREFIX = ["s", "d", "f", "v", "x"]
// const STRING_PREFIX = ["0", ",", "n", "h", "j", "u", "k", "i", "l", "o", "ju", "ki", "lo", "V"]

const HUI_PREFIX = ["s", "d", "f", "v", "x"]
const STRING_PREFIX = [",", "n", "h", "j", "u", "k", "i", "l", "o", "ju", "ki", "lo", "V", "c", "U", "banlun", "lun", "bs", "ds", "cs", "dj", "/", ">", "\\"]
// orig: had 0

const CHORD_KEYS = ["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"]

// unflatten charMap
let jzpMap = {}
// let spacers = charMap.spacers
// for (let key in charMap) {
//   if (key.indexOf("__") == -1) {
//     continue
//   }
//   const l = key.split("__")[0]
//   const a = key.split("__")[1]
//   if (jzpMap[l] == undefined) {
//     jzpMap[l] = {}
//     jzpMap[l].width = charMap[key].layoutWidth
//   }
//   if (jzpMap[l][a] == undefined) {
//     jzpMap[l][a] = charMap[key]
//   }
//   // charMap = newCharMap
// }
// jzpMap = jzpMap

for (let key in charMap) {
  if (key != "spacer" && key != "spacers") {
    jzpMap[key] = charMap[key]
    jzpMap[key].advanceUnicode = charMap.spacers[String(charMap[key].width)].unicode
  }
}



function _sortArrayByKeyDesc(array, key) {
  return array.sort((a, b) => {
    if (a[key].length < b[key].length) {
      return 1;
    }
    if (a[key].length > b[key].length) {
      return -1;
    }
    return 0;
  });
}

// separate string and hui
function _separateHuiString(str, ch) {
  let lastChar = str.slice(-1)
  if (Number(lastChar) >= 1 && Number(lastChar) <= 7) {
    let stringNum = lastChar
    str = str.slice(0, -1) + ch + stringNum // hack: insert a "l" here to break up the hui and string numbers, will remove a few lines down
  }
  return str
}

// console.debug("jzpMap", jzpMap)

function _findFirstPluckIndex(str) {
  const indices = plucks.map(pluck => str.indexOf(pluck));
  const minIndex = Math.min(...indices.filter(index => index !== -1));
  return minIndex === Infinity ? -1 : minIndex;
}
// exclude: qia qi (c), yan (V)
// s4, s43 => 4.3, s10 => 10,
function _getLeftHandObj(str) {
  const posIdx = leftHandPositions.findIndex(pos => str.indexOf(pos) > -1);
  const pos = posIdx === -1 ? null : leftHandPositions[posIdx];
  
  const numbers = str.trim().split(/(\d+(?:\.\d+)?)/).filter(e => !isNaN(e) && e != "") // => ["3", "3.14"]
  if (numbers.length > 1) {
    // console.warn("more than one number detected in lefthand part, will just use the first number", str, numbers)
  }
  let num = numbers.length === 0 ? null : numbers[0];
  // convert number to decial (ex: 55 => 5.5, 102 => 10.2, 12 != 1.2)
  if (num != null) {
    if (num.indexOf(".") > -1) {
      num = Number(num)
    }
    else {
      if (num.length >= 3) {
        if  (num.slice(0, 2) === "10" || num.slice(0, 2) === "11" || num.slice(0, 2) === "12" || num.slice(0, 2) === "13") {
          num = num.slice(0, 2) + "." + num.slice(2)
          num = Number(num)
        }
        else {
          num = num.slice(0, 1) + "." + num.slice(1)
          num = Number(num)
        }
      }
      else if (num.length == 2) {
        if (["10", "11", "12", "13"].indexOf(num) == -1) {
          num = num.slice(0, 1) + "." + num.slice(1)
          num = Number(num)
        }
        else {
          num = Number(num)
        }
      }
      else {
        num = Number(num)
      }
    }
  }

  return {
    fingering: pos,
    hui: num == null ? null : Number(num)
  }
}
function _getRightHandObj(str) {
  // get positions: ki5 => ["ki"], "/k5" => ["/", "k"]
  let positions = []
  let positionString = str
  plucks.forEach(pluck => {
    if (positionString.indexOf(pluck) > -1) {
      positions.push(pluck)
      positionString = positionString.replace(pluck, "")
    }
  })

  // get string numbers: 54 => ["5", "4"]
  let numbers = str.trim().split(/(\d+(?:\.\d+)?)/).filter(e => !isNaN(e) && e != "") // "x3x3.14"=> ["3", "3.14"]
  if (numbers.length > 1) {
    // console.warn("more than one number detected in righthand part, will just use the first number", str, numbers)
  }
  let nums = numbers.length === 0 ? null : numbers[0].split("");
  if (nums != null) 
    nums = nums.filter(e => !isNaN(e) && e != "")  // ["3", ".", "4"] => ["3", "4"]
  
  let arabicToChinese = [null, "s1", "s2", "s3", "四", "五", "六", "七"]
  if (nums != null) {
    nums = nums.map(num => "s" + num)
  }
  return {
    fingerings: positions,
    strings: nums		
  }
}
function _isLeftHandNull(charObj) {
  return charObj.left.fingering == null && charObj.left.hui == null
}
function _unionExists(a, b) {
  return a.filter(element => b.includes(element)).length > 0
}
function _babelfish(str, from, to) {
  babel.map(e => {
    if (e[from] == "") return
    if (e.category == "char") return
    str = str.replaceAll(e[from], e[to])
    str = str.replaceAll(e[from], e[to])
  })	
  return str
}

// opts: {category: "C", side: "left"}
function _stringToCharacter(str, opts = {}) {
  // Case 1: mini characters, directly return unicode
  // const singleChar = babel.filter(e => e.category == "char" && e.key == str)
  if (str[0] == "#") {
    str = str.replace("#", "")
    let bStr = str == "" ? "" : babel.filter(e => e.category == "char" && (e.cs == str || e.ct == str || e.other == str || e.key == str))[0]?.key
    // console.debug("case 1, standalone character", str, bStr)
    return String.fromCharCode(charMap.layout_char1__area_char.components.filter(e => e.keys.includes(bStr))[0]?.unicode)
    // return String.fromCharCode(charMap.char1.areas.char.components.filter(e => e.keys.includes(bStr))[0]?.unicode)
  }

  // Case 2: verticals
  if (str[0] == ":") {
    // console.debug("case 2, vertical characters", str)
    let chars = str.replace(":", "")
    if (chars.includes(",")) 
      chars = chars.split(",").filter(e => e != "")
    else 
      chars = chars.replace("璅", "").split("").filter(e => e != "")
    // console.debug(chars)
    let uniStr = ""
    let layout = "layout_char" + chars.length
    if (chars.length == 1) {
      let ch = chars[0]
      let bCh = ch == "" ? "" : babel.filter(e => e.category == "char" && (e.cs == ch || e.ct == ch || e.other == ch || e.key == ch))[0]?.key
      uniStr += String.fromCharCode(charMap.layout_char1__area_char.components.find(e => e.keys.includes(bCh))?.unicode)
    }
    else {
      chars.map((ch, i) => {
        let bCh = ch == "" ? "" : babel.filter(e => e.category == "char" && (e.cs == ch || e.ct == ch || e.other == ch || e.key == ch))[0]?.key
        uniStr += String.fromCharCode(charMap[layout + "__area_char"+(i+1)]?.components?.find(e => e.keys.includes(bCh))?.unicode)
      })
    }
    return uniStr
  }

  // Case 3: number string
  if (["1", "2", "3", "4", "5", "6", "7", "一", "二", "三", "四", "五", "六", "七"].includes(str)) {
    // console.debug("case 3, number", str)
    let bStr = babel.filter(e => e.category == "char" && (e.cs == str || e.ct == str || e.other == str || e.key == str))[0]?.key
    return String.fromCharCode(charMap.layout_char1__area_char.components.filter(e => e.keys.includes(bStr))[0]?.unicode)
  }

  // Case 3: jianzipu, more commplicated to get all the info to construct unicodes
  // parse left v. right hand instructions (fingering v. hui v. string)
  // console.debug("case 4, jianzipu", str)
  let leftRightDivideIdx = _findFirstPluckIndex(str)
  let leftStr, rightStr
  if (isNaN(str) || str.includes("o")) {	// str is not a number, apparently 0o3 evaluates to a number hence the special case for containing "o"
    leftStr = leftRightDivideIdx == -1 ? str : str.slice(0, leftRightDivideIdx)
    rightStr = leftRightDivideIdx == -1 ? "" : str.slice(leftRightDivideIdx)
    // console.debug("lvr", leftStr, rightStr, str)
  }
  else { // str is just a number, indicating it's a string, not a hui position
    if (str.length == 2 && str[0] == "0") {
      leftStr = str[0]
      rightStr = str[1]
    }
    else if (Number(str) >= 1 && Number(str) <= 7) {
      leftStr = ""
      rightStr = str
    }
    else {
      leftStr = str
      rightStr = ""
    }
  }

  const charObj = {
    ogStr: str,
    leftStr: leftStr,
    rightStr: rightStr,
    left: _getLeftHandObj(leftStr),
    right: _getRightHandObj(rightStr),
    keys: [],
    strMap: null
  }
  // push spacer "_"
  if (str.includes("_")) {
    charObj.keys.push("_")
  }

  // left hand hui, case of partial hui and 13+
  if (String(charObj.left.hui).includes(".")) {
    if (charObj.left.hui > 13) {
      charObj.keys.push("13+")
    }
    else {
      charObj.keys.push(String(charObj.left.hui).split(".")[0] + ".")
      charObj.keys.push("." + String(charObj.left.hui).split(".")[1])
    }
  }
  else {
    charObj.keys.push(String(charObj.left.hui))
  }

  if (charObj.left.fingering != null) 
    charObj.keys.push(charObj.left.fingering)
  charObj.right.fingerings = charObj.right.fingerings == null ? [] : charObj.right.fingerings
  charObj.right.strings = charObj.right.strings == null ? [] : charObj.right.strings
  charObj.keys = [...charObj.keys, ...charObj.right.fingerings]
  if (charObj.right.strings.length < 2) {
    charObj.keys = [...charObj.keys, ...charObj.right.strings]
  }
  else {
    charObj.keysMultiString = charObj.right.strings
  }
  // console.debug('charObj', charObj, charObj.keys, opts)

  // determine layout
  let layout = "" // "layout_tiao" // default
  if (opts.category == undefined) {
    optimum = findOptimalLayout(charObj.keys) //, "*", jzpMap)
    if (optimum.length > 0) {
      layout = optimum[0]
    }
  }
  else { // chords (cuo, etc.)
    if (["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"].includes(opts.category)) {
      let filter = []
      if (opts.side == "left") {
        filter = ["layout_cuo_left", "layout_cuo_v2_left", "layout_cuo_v3_left"]
      }
      else if (opts.side == "right") {
        filter = ["layout_cuo_right", "layout_cuo_v2_right", "layout_cuo_v3_left"]
      }
      layout = findOptimalLayout(charObj.keys, filter)[0]
    }
  }
  // console.debug("using", layout)

  // find unicode character & construct unicode string
  let character = ''
  for (let area in jzpMap[layout]) {
    if (area == "area_string_top" || area == "area_string_bottom") continue // for Li (ex: L43)
    for (let i=0; i<jzpMap[layout][area].components.length; i++) {
      if (jzpMap[layout][area].components[i].keys.some(v => charObj.keys.includes(v))) {
        // console.debug('found', layout, area, jzpMap[layout][area].components[i],jzpMap[layout][area])
        character += String.fromCharCode(jzpMap[layout][area].components[i].unicode)
      }
    }
  }
  // multistring
  if (charObj.keysMultiString) {
    if (jzpMap[layout]["area_string_top"] != undefined)
      character += String.fromCharCode(jzpMap[layout]["area_string_top"].components.find(e => e.keys.includes(charObj.keysMultiString[0])).unicode)
    if (jzpMap[layout]["area_string_bottom"] != undefined)
      character += String.fromCharCode(jzpMap[layout]["area_string_bottom"].components.find(e => e.keys.includes(charObj.keysMultiString[1])).unicode)
  }


  return character
}

// #region latest 3 functions: getKeyArray --> findOptimalLayout --> getUnicode
// k3 => ["k", "3"], etc
function getKeyArray(str) {
  str = str.replaceAll("分", ".")
  str = str.replaceAll(".", "..")

  let uberBabel = babelfish.sort(((a, b) => b.translation.length - a.translation.length))

  let idx = 0
  let ctr = 0
  let arr = []
  do {
    let matches = uberBabel.filter(e => e.translation == str.slice(idx, idx + e.translation.length))
    if (matches.length > 0) {
      arr.push(matches[0].key)
      idx += matches[0].translation.length
    }
    else {
      arr.push(str[idx])
      idx++
    }

    ctr++
  } while (idx < str.length && ctr < 50)

  // case: return early if it's a character (#) or vertical phrase (:)
  if (arr[0] == ":" || arr[0] == "#") {
    return arr
  }

  // CASE: convert numbers to strings
  function isStringable(str) {
    return str && !isNaN(str) && Number(str) >= 1 && Number(str) <= 7
  }
  
  // case: if last element is number, mark it as string
  const lastElement = arr[arr.length-1]
  if (isStringable(lastElement)) {
    arr[arr.length-1] = "S" + arr[arr.length-1]
  }
  // case: if is chord, last element before | is number, then mark it as string
  if (arr.filter(e => CHORD_KEYS.includes(e)).length > 0) {
    // last key before | if number --> mark it as String
    const separatorIdx = arr.findIndex(e => e == "|")
    if (separatorIdx > -1 && isStringable(arr[separatorIdx-1])) {
      arr[separatorIdx-1] = "S" + arr[separatorIdx-1]
    }
  }
  // case: li --> up to next two are strings
  const liIdx = arr.findIndex(e => e == "U")
  if (liIdx > -1) {
    if (isStringable(arr[liIdx+1])) {
      arr[liIdx+1] = "S" + arr[liIdx+1]
    }
    if (isStringable(arr[liIdx+2])) {
      arr[liIdx+2] = "S" + arr[liIdx+2]
    }
  }

  // CASE: convert hui numbers to hui decimals (ex: 75 -> 7. and .5)
  arr.map((e, i) => {
    if (!isNaN(e) && !isNaN(arr[i+1])) {
      if (arr[i].indexOf(".") == -1) 
        arr[i] = arr[i] + "."
      if (arr[i+1].indexOf(".") == -1)
        arr[i+1] = "." + arr[i+1]
    }
  })

  return arr.filter(e => e != undefined)
}
// keys: array of keys to match
// filter: array of layouts to limit
function findOptimalLayout(keys, filter = []) {
  let results = []
  let maxMatchCount = 0
  for (let layout in jzpMap) {
    let result = {
      layout: layout,
      matches: keys.map(k => {return {key: k, areas: []}}),
      nomatches: [], 
      matchCount: 0,
      advanceUnicode: jzpMap[layout].advanceUnicode
    }
    if (filter.length != 0  && filter.indexOf(layout) == -1) continue
    for (let area in jzpMap[layout].areas) {
      let match = false
      for (let i=0; i<jzpMap[layout].areas[area].components.length; i++) {
        if (keys.filter(k => jzpMap[layout].areas[area].components[i].keys.includes(k)).length > 0) {
          match = true
          let keyMatch = keys.filter(k => jzpMap[layout].areas[area].components[i].keys.includes(k))[0]
          
          if (result.matches.indexOf(area) == -1) {
            result.matches.map(m => {
              if (m.key == keyMatch) {
                m.areas.push(area)
              }
            })
          }
        }
      }
      if (!match) {
        result.nomatches.push(area)
      }
    }
    result.matchCount = result.matches.filter(m => m.areas.length > 0).length
    result.areasWithoutKeys = result.nomatches.length
    maxMatchCount = Math.max(maxMatchCount, result.matchCount)

    // let r = result

    let claimedAreas = []
    let keysWithoutAreas = 0
    let cuoSide = 1
    let isCuo = keys.filter(k => ["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"].includes(k)).length > 0
    let isLi = keys.includes("U")
    let isMultiString = false

    result.matches.map((m, i) => {
      // "claim" the first area alphabetically
      // if (cuoSide == 2) {
      //   m.areas = m.areas.filter(a => a.indexOf("_2") > -1)
      // }
      m.areas.sort()
      let areaOptions = m.areas.filter(a => !claimedAreas.includes(a))
      if (areaOptions.length > 0) {
        // case: multistring (li / U)
        if (isLi && areaOptions.includes("string")) {
          if (result.matches[i+1] && result.matches[i+1].areas.includes("string")) {
            isMultiString = true
          }
          if (isMultiString) {
            areaOptions = areaOptions.filter(a => a != "string")
            areaOptions.reverse()
          }
          else {
            areaOptions = areaOptions.filter(a => a == "string")
          }
        }

        m.useArea = areaOptions[0]

        // // case: cuo/chords, IF chord --> hui v. hui2, string v. string2, etc.
        // if (isCuo && (m.useArea == "string" || m.key == "|")) {
        //   cuoSide = 2
        // }
        claimedAreas.push(areaOptions[0])
      }
      else {
        m.useArea = undefined
        keysWithoutAreas++
      }
    })
    result.keysWithoutAreas = keysWithoutAreas

    results.push(result)
  }
 
  // keys without areas (filter)
  results.sort((a, b) => a.keysWithoutAreas - b.keysWithoutAreas)
  results = results.filter(r => r.keysWithoutAreas == results[0].keysWithoutAreas)

  // areas without keys (filter)
  results.sort((a, b) => a.areasWithoutKeys - b.areasWithoutKeys)
  results = results.filter(r => r.areasWithoutKeys == results[0].areasWithoutKeys)

  const winnerMap = results[0].matches.map(e => { return {key: e.key, area: e.useArea, options: e.areas} })
  return {
    layout: results[0].layout,
    data: winnerMap,
    winnerMapStringified: JSON.stringify(winnerMap),
    options: results
  }
}
// ex: [{"key":"s","area":"left"},{"key":"7.","area":"hui…"k","area":"right"},{"key":"S3","area":"string"}]
function getUnicode(layout, obj, includeSpacer = true) {
  const unicodeArr = obj.map(o => {
    return jzpMap[layout].areas[o.area]?.components.filter(c => c.keys.includes(o.key))[0].unicode
  }).filter(e => e != undefined)
  // const unicodes = unicodeArr.join("")
  if (includeSpacer == true) {
    unicodeArr.push(jzpMap[layout].advanceUnicode)
  }

  const unicodes = unicodeArr.map(u => String.fromCharCode(u)).join("")
  return {unicodes, unicodeArr}
}
// #endregion

export function stringToCharObj(str, v = 2) {
  // Case 1: mini characters, directly return unicode
  if (str[0] == "#" ) {
    return convert(str)
  }

  // Case 2: verticals
  if (str[0] == ":") {
    return convert(str)
  }

  // Case 3: number string
  if (["1", "2", "3", "4", "5", "6", "7", "一", "二", "三", "四", "五", "六", "七"].includes(str)) {
    return convert(str)
  }

  // Case 4: jianzipu, more commplicated to get all the info to construct unicodes

  if (v == 2) {
    const keys = getKeyArray(str)
    const letters = str.split("")
    const split = letters.findIndex(k => STRING_PREFIX.includes(k))
    const rightStartIdx = keys.findIndex(k => STRING_PREFIX.includes(k) || k[0] == "S")
    const leftArr = keys.slice(0, rightStartIdx)
    const rightArr = keys.slice(rightStartIdx)
    const hui = leftArr.filter(e => !isNaN(e)).join("").replace("..", ".")
  
    const charObjV2 = {
      ogStr: str,
      leftStr: letters.slice(0, split).join(""),
      rightStr: letters.slice(split).join(""),
      left: {
        fingering: leftArr.filter(e => HUI_PREFIX.includes(e))[0] || null,
        hui: hui == "" ? null : Number(hui)
      },
      right: {
        fingerings: rightArr.filter(e => plucks.includes(e)),
        strings: rightArr.filter(e => e[0] == "S")
      },
      keys: keys
    }
    return charObjV2

  }


  // parse left v. right hand instructions (fingering v. hui v. string)
  // console.debug("case 4, jianzipu", str)
  let leftRightDivideIdx = _findFirstPluckIndex(str)
  let leftStr, rightStr
  if (isNaN(str) || str.includes("o")) {	// str is not a number, apparently 0o3 evaluates to a number hence the special case for containing "o"
    leftStr = leftRightDivideIdx == -1 ? str : str.slice(0, leftRightDivideIdx)
    rightStr = leftRightDivideIdx == -1 ? "" : str.slice(leftRightDivideIdx)
  //   console.debug("lvr", leftStr, rightStr, str)
  }
  else { // str is just a number, indicating it's a string, not a hui position
    if (str.length == 2 && str[0] == "0") {
      leftStr = str[0]
      rightStr = str[1]
    }
    else if (Number(str) >= 1 && Number(str) <= 7) {
      leftStr = ""
      rightStr = str
    }
    else {
      leftStr = str
      rightStr = ""
    }
  }

  const charObj = {
    ogStr: str,
    leftStr: leftStr,
    rightStr: rightStr,
    left: _getLeftHandObj(leftStr),
    right: _getRightHandObj(rightStr),
    keys: [],
    strMap: null
  }
  // push spacer "_"
  if (str.includes("_")) {
    charObj.keys.push("_")
  }

  // left hand hui, case of partial hui and 13+
  if (String(charObj.left.hui).includes(".")) {
    if (charObj.left.hui > 13) {
      charObj.keys.push("13+")
    }
    else {
      charObj.keys.push(String(charObj.left.hui).split(".")[0] + ".")
      charObj.keys.push("." + String(charObj.left.hui).split(".")[1])
    }
  }
  else {
    charObj.keys.push(String(charObj.left.hui))
  }

  if (charObj.left.fingering != null) 
    charObj.keys.push(charObj.left.fingering)
  charObj.right.fingerings = charObj.right.fingerings == null ? [] : charObj.right.fingerings
  charObj.right.strings = charObj.right.strings == null ? [] : charObj.right.strings
  charObj.keys = [...charObj.keys, ...charObj.right.fingerings]
  if (charObj.right.strings.length < 2) {
    charObj.keys = [...charObj.keys, ...charObj.right.strings]
  }
  else {
    charObj.keysMultiString = charObj.right.strings
  }
  return charObj
}

export function getKeyString(word) {
  if (word[0] != ":" && word[0] != "#") {
    word = _babelfish(word, "cs", "key")
    word = _babelfish(word, "ct", "key")
    word = _babelfish(word, "other", "key")
  }
  return word
}

export function getCharacter(word, includeSpacer = true) {
  // console.debug("getCharacter", word)

  // get spacer
  const spacerUnicode = charMap.spacer?.unicode
  const spacer = spacerUnicode == undefined ? "" : String.fromCharCode(spacerUnicode)

  if (word[0] != ":" && word[0] != "#") {
    word = _babelfish(word, "cs", "key")
    word = _babelfish(word, "ct", "key")
    word = _babelfish(word, "other", "key")
  }
  
  let translation
  if (chords.some(e => word.includes(e))) {  // chords, split chords into left + category/divider + right
    let category = chords.filter(e => word.includes(e))[0]
    let sideLeft = word.split("|")[0].replace(category, "")
    let sideRight = word.split("|")[1]
    // console.debug("chord", category, sideLeft, sideRight)
    if (sideLeft?.indexOf(",") == -1)
      sideLeft = _separateHuiString(sideLeft, ",")
    if (sideRight?.indexOf(",") == -1)
      sideRight = _separateHuiString(sideRight, ",")
    translation = _stringToCharacter(sideLeft, {category: category, side: "left"}) 
    translation += _stringToCharacter(category, {category: category, side: "left"}) 
    if (sideRight != undefined)
      translation += _stringToCharacter(sideRight, {category: category, side: "right"})
  }
  else { // standard jianzipu + characters
    translation = _stringToCharacter(word)
  }
  const character = translation == '' && word != '' ? word : translation + (includeSpacer ? spacer : "")
  return character
}
export function convert(para) {
  para = para.replaceAll("：", ":")
    .replaceAll("-", " ")
    .replaceAll("　", " ")
    .replaceAll("｜", "|")

  // check for v1 parenetheses indictaor
  if (para.includes("(") && para.includes(")")) {
    // console.warn("Is this v1 of JianZiPu? If so, please convert to v2 first. In the UI, click 'Convert from V1' button. With the API, use v1tov2() method.")
  }

  // split into lines and process
  var lines = para.split('\n')
  for (var j=0;j<lines.length; j++) {
    if (lines[j] == undefined) continue
    var words = lines[j].split(' ')
    for (var i=0;i<words.length;i++) {
      // words[i] = getCharacter(words[i], false)
      const keys = getKeyArray(words[i])

      // case: chords, split left and right side
      if (CHORD_KEYS.some(e => keys.includes(e))) {
        const separatorIdx = keys.indexOf("|") == -1 ? keys.length : keys.indexOf("|")
        // left side
        let left = keys.slice(0, separatorIdx)
        let { layout: layoutLeft, data: dataLeft } = findOptimalLayout(left, ["cuo_left", "cuo_v2_left", "cuo_v3_left"])
        let leftUnicodes = getUnicode(layoutLeft, dataLeft).unicodes

        // right side
        let right = keys.slice(separatorIdx+1)
        let { layout: layoutRight, data: dataRight } = findOptimalLayout(right, ["cuo_right", "cuo_v2_right", "cuo_v3_right"])
        let rightUnicodes = getUnicode(layoutRight, dataRight).unicodes
        
        // combine
        words[i] = leftUnicodes + rightUnicodes
      }
      // case: # or :
      else if (keys[0] == "#" || keys[0] == ":") {
        const { layout, data } = findOptimalLayout(keys, ["char1", "char2", "char3", "char4"])
        
        // console.log("layout", words[i], layout, data)
        words[i] = getUnicode(layout, data).unicodes
      }
      // case: normal jianzipu
      else {
        const { layout, data } = findOptimalLayout(keys)
        // console.log("layout", words[i], layout, data)
        words[i] = getUnicode(layout, data).unicodes
      }

    }
    // lines[j] = words.join('　') // note: this is the ideographic space, not the regular space. String.fromCharCode(12288)
    lines[j] = words.join(' ') 
  }
  lines = lines.join('\n')
  return lines
}
export function v1tov2(para) {
  para = _babelfish(para, "cs", "key")
  para = _babelfish(para, "ct", "key")
  para = _babelfish(para, "other", "key")
  var lines = para.split('\n')
  lines.map((line, i) => {
    var words = line.split(' ')
    words.map((word, j) => {
      // characters
      if (babel.filter(e => e.category == "char" && e.key == word).length > 0) {
        words[j] = "#" + word
      }

      // compound
      else if (word.includes("-")) {
        let wordParts = word.split("-")
        let newStr = wordParts.map(e => v1tov2(e)).join("-")
        words[j] = newStr
      }

      // verticals (guqin composer)
      else if (word.includes("/")) {
        let chars = word.split("/")
        let newStr = ":" + chars.join(",")
        words[j] = newStr
      }

      // chords
      else if (babel.filter(e => e.category == "chord" && word.includes(e.key)).length > 0) {
        // words[j] = "CHORD"
        let chord = babel.filter(e => e.category == "chord" && word.includes(e.key))[0].key
        let chordString = word.replace(chord, "|")
        let left = chordString.split("|")[0]
        let right = chordString.split("|")[1]
        words[j] = chord + v1tov2(left) + "|" + v1tov2(right)
      }

      else {
        // get hui
        let hui = word.match(/\((.*?)\)/)?.[1]
        let huiLessStr = word.replace("("+hui+")", "")
  
        // get other elements
        let elements = []
        let babelDesc = babel.filter(e => e.category != "char").sort((a, b) => b.key.length - a.key.length)
        babelDesc.map(e => {
          if (huiLessStr.includes(e.key)) {
            elements.push([e.key, e.category, e.leftVsRightSeparator])
            huiLessStr = huiLessStr.replaceAll(e.key, "")
          }
        })
        // console.debug("elements", elements)

        let newStr = elements.filter(e => e[2] != "yes" && e[1] != "number").map(e => e[0]).join("") 
        newStr += hui == undefined ? "" : hui
        newStr += elements.filter(e => e[2] == "yes").map(e => e[0]).join("") 
        newStr += elements.filter(e => e[1] == "number").map(e => e[0]).join("") 

        words[j] = newStr
      }

    })
    lines[i] = words.join(' ') // regular space
  })
  return lines.join('\n')
}

if (typeof document !== 'undefined') {
	document.addEventListener("DOMContentLoaded", function(event) { 
		let jzpInBrackets = document.getElementsByClassName("jzp")
		// var jianzipu = new JZP()
		for (var i=0;i<jzpInBrackets.length;i++) {
			let newDivHTML = jzpInBrackets[i].innerHTML
			newDivHTML = newDivHTML.replaceAll('[[[', '<span class="jzp-font jzp-characters">').replaceAll(']]]', '</span>')
			newDivHTML = newDivHTML.replaceAll('[[', '<span class="jzp-font">').replaceAll(']]', '</span>')
			jzpInBrackets[i].innerHTML = newDivHTML
			let jzpInCharacters = jzpInBrackets[i].getElementsByClassName("jzp-characters")
			for (var j=0;j<jzpInCharacters.length;j++) {
				jzpInCharacters[j].innerText = convert(jzpInCharacters[j].innerText)
			}
		}
	})
}