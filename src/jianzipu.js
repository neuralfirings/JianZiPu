import charMap from './charMap.json'
import babelfish from './babelDict.json'
if (typeof window !== 'undefined') {
  import('./jianzipu.css');
}

// constants
const HUI_PREFIX = ["s", "d", "f", "v", "x"]
const STRING_PREFIX = [",", "n", "h", "j", "u", "k", "i", "l", "o", "ju", "ki", "lo", "V", "c", "U", "banlun", "lun", "bs", "ds", "cs", "dj", "/", ">", "\\"]
const CHORD_KEYS = ["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"]

// remove spacders from charMap --> jzpMap
let jzpMap = {}
for (let key in charMap) {
  if (key != "spacer" && key != "spacers") {
    jzpMap[key] = charMap[key]
    jzpMap[key].advanceUnicode = charMap.spacers[String(charMap[key].width)].unicode
  }
}


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
    let isSubChar = false
    arr.map((e, i) => {
      if (e == "[") {
        isSubChar = true
      }
      else if (e == "]") {
        isSubChar = false
      }

      if (isSubChar == true) {
        if (!isNaN(e) && !isNaN(arr[i+1])) {
          if (arr[i].indexOf(".") == -1) 
            arr[i] = arr[i] + "."
          if (arr[i+1].indexOf(".") == -1)
            arr[i+1] = "." + arr[i+1]
        }
      }
    })
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
    let isSubChar = false
    let currCharInVert = 1

    result.matches.map((m, i) => {
      // m = { key: "5", areas: ["left", "right"], useArea: undefined }

      if (layout.slice(0,7) == "vertjzp") {
        // if vertjzp, check for subChar, then sort according to preset order
        if (m.key == "[") {
          isSubChar = true
        }
        else if (m.key == "]") {
          isSubChar = false
          currCharInVert++
        }

        let newOrder = isSubChar === true ? [ "left_" + currCharInVert, "hui_" + currCharInVert, "hui_small_top_" + currCharInVert, "hui_small_bottom_" + currCharInVert] : [ "char" + currCharInVert ]
        newOrder = newOrder.filter(a => m.areas.includes(a))
        m.areas = newOrder
      }
      else {
        // if not vertjzp, sort alphabetically
        m.areas.sort()
      }

      //  "claim" the first area in sorted order
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
        claimedAreas.push(areaOptions[0])

        if (layout.slice(0,7) == "vertjzp") {
          if (areaOptions[0].indexOf("char") > -1) {
            currCharInVert++
          }
        }
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

// EXPORTS
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
        fingerings: rightArr.filter(e => STRING_PREFIX.includes(e) && e != ","),
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

export function convert(para) {
  para = para.replaceAll("：", ":")
    .replaceAll("-", " ")
    .replaceAll("　", " ")
    .replaceAll("｜", "|")
    .replaceAll("【", "[")
    .replaceAll("】", "]")

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
      // case: ::
      else if (keys[0] == ":" && keys[1] == ":") {
        const { layout, data } = findOptimalLayout(keys, ["vertjzp1", "vertjzp2", "vertjzp3", "vertjzp4"])
        
        // console.log("layout", words[i], layout, data)
        words[i] = getUnicode(layout, data).unicodes
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

// If DOM look for jzp classes and brackets to convert to unicodes
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