import charMap from './charMap.json'
import babelDict from './babel.json'
if (typeof window !== 'undefined') {
  import('./jianzipu.css');
}

const babel = _sortArrayByKeyDesc(babelDict, "key")
const plucks = babel.filter(e => e.leftVsRightSeparator == "yes").map(e => e.key)
const leftHandPositions = babel.filter(e => e.category == "left").map(e => e.key)
const chords = babel.filter(e => e.category == "chord").map(e => e.key)

// unflatten charMap
let jzpMap = {}
for (let key in charMap) {
  if (key.indexOf("__") == -1) {
    continue
  }
  const l = key.split("__")[0]
  const a = key.split("__")[1]
  if (jzpMap[l] == undefined) {
    jzpMap[l] = {}
  }
  if (jzpMap[l][a] == undefined) {
    jzpMap[l][a] = charMap[key]
  }
  // charMap = newCharMap
}
// jzpMap = jzpMap



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
    console.warn("more than one number detected in lefthand part, will just use the first number", str, numbers)
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
    console.warn("more than one number detected in righthand part, will just use the first number", str, numbers)
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
    console.debug("case 1, standalone character", str, bStr)
    return String.fromCharCode(charMap.layout_char1__area_char.components.filter(e => e.keys.includes(bStr))[0]?.unicode)
  }

  // Case 2: verticals
  if (str[0] == ":") {
    console.debug("case 2, vertical characters", str)
    let chars = str.replace(":", "")
    if (chars.includes(",")) 
      chars = chars.split(",").filter(e => e != "")
    else
      chars = chars.split("").filter(e => e != "")
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
    console.debug("case 3, number", str)
    let bStr = babel.filter(e => e.category == "char" && (e.cs == str || e.ct == str || e.other == str || e.key == str))[0]?.key
    return String.fromCharCode(charMap.layout_char1__area_char.components.filter(e => e.keys.includes(bStr))[0]?.unicode)
  }

  // Case 3: jianzipu, more commplicated to get all the info to construct unicodes
  // parse left v. right hand instructions (fingering v. hui v. string)
  console.debug("case 4, jianzipu", str)
  let leftRightDivideIdx = _findFirstPluckIndex(str)
  let leftStr, rightStr
  if (isNaN(str) || str.includes("o")) {	// str is not a number, apparently 0o3 evaluates to a number hence the special case for containing "o"
    leftStr = leftRightDivideIdx == -1 ? str : str.slice(0, leftRightDivideIdx)
    rightStr = leftRightDivideIdx == -1 ? "" : str.slice(leftRightDivideIdx)
    console.debug("lvr", leftStr, rightStr, str)
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
  console.debug('charObj', charObj, charObj.keys, opts)

  // determine layout
  let layout = "layout_tiao" // was: tiao
  if (opts.category == undefined) {
    if (_unionExists(charObj.right.fingerings, ["n"]))
      if (_isLeftHandNull(charObj))
        layout = "layout_bo_rt"
      else
        layout = "layout_bo"
    else if (charObj.left.fingering == "c") // qiaqi
      layout = "layout_bo"
    else if (_unionExists(charObj.right.fingerings, ["h"]))	
      if (_isLeftHandNull(charObj))
        layout = "layout_tuo_rt"
      else
        layout = "layout_tuo"
    else if (_unionExists(charObj.right.fingerings, ["ju", "uj", "j", "V", "lun", "banlun"]))
      if (_isLeftHandNull(charObj))
        layout = "layout_mo_rt"
      else
        if (_unionExists(charObj.right.fingerings, ["/", ">"]))
          layout = "layout_mo_chuo"
        else
          layout = "layout_mo"
    else if (_unionExists(charObj.right.fingerings, ["u", "c"]))
      if (_isLeftHandNull(charObj))
        layout = "layout_tiao_rt"
      else
        layout = "layout_tiao"
    else if (_unionExists(charObj.right.fingerings, ["k", "l"]))
      if (_isLeftHandNull(charObj))
        layout = "layout_gou_rt"
      else
        if (_unionExists(charObj.right.fingerings, ["/", ">"]))
          layout = "layout_gou_chuo"
        else
          layout = "layout_gou"
    else if (_unionExists(charObj.right.fingerings, ["i", "o"]))
      if (_isLeftHandNull(charObj))
        layout = "layout_ti_rt"
      else
        if (_unionExists(charObj.right.fingerings, ["/", ">"]))
          layout = "layout_ti_chuo"
        else
          layout = "layout_ti"
    else if (_unionExists(charObj.right.fingerings, ["ki", "ik"])) 
      if (_isLeftHandNull(charObj))
        layout = "layout_gouti_rt"
      else
        if (_unionExists(charObj.right.fingerings, ["/", ">"]))
          layout = "layout_gouti_chuo"
        else
          layout = "layout_gouti"
    else if (_unionExists(charObj.right.fingerings, ["lo", "ol"])) 
      if (_isLeftHandNull(charObj))
        layout = "layout_dazhai_rt"
      else
        if (_unionExists(charObj.right.fingerings, ["/", ">"]))
          layout = "layout_dazhai_chuo"
        else
          layout = "layout_dazhai"
    else if (_unionExists(charObj.right.fingerings, ["U"]))
      layout = "layout_li"
    else if (_unionExists(charObj.right.fingerings, ["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"]))
      if (charObj.left.fingering == null && charObj.left.hui == null)
        layout = "layout_cuo_v2_left"	
      else
        layout = "layout_cuo_left"
  }
  else {
    if (["C", "DC", "FC", "TTT", "TT", "BL", "B", "L"].includes(opts.category))
      if (charObj.left.fingering == null && charObj.left.hui == null)
        layout = "layout_cuo_v2_" + opts.side	
      else
        layout = "layout_cuo_" + opts.side	
  }
  // console.debug("using", layout)

  // find unicode character & construct unicode string
  let character = ''
  for (let area in jzpMap[layout]) {
    if (area == "area_string_top" || area == "area_string_bottom") continue // for Li (ex: L43)
    for (let i=0; i<jzpMap[layout][area].components.length; i++) {
      if (jzpMap[layout][area].components[i].keys.some(v => charObj.keys.includes(v))) {
        console.debug('found', layout, area, jzpMap[layout][area].components[i],jzpMap[layout][area])
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

export function getCharacter(word, includeSpacer = true) {
  console.debug("getCharacter", word)

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
    console.debug("chord", category, sideLeft, sideRight)
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
  para = para.replaceAll("-", " ")
  para = para.replaceAll("　", " ")

  // check for v1 parenetheses indictaor
  if (para.includes("(") && para.includes(")")) {
    console.warn("Is this v1 of JianZiPu? If so, please convert to v2 first. In the UI, click 'Convert from V1' button. With the API, use v1tov2() method.")
  }

  // split into lines and process
  var lines = para.split('\n')
  for (var j=0;j<lines.length; j++) {
    if (lines[j] == undefined) continue
    var words = lines[j].split(' ')
    for (var i=0;i<words.length;i++) {
      words[i] = getCharacter(words[i], false)
    }
    lines[j] = words.join('　') // note: this is the ideographic space, not the regular space. String.fromCharCode(12288)
    // lines[j] = words.join(' ') 
  }
  lines.map((e, i)=> {
    if (e[e.length-1] != '　') {
      lines[i] += '　'
    }
  })
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
        console.debug("elements", elements)

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