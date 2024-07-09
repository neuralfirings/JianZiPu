const fs = require('fs');

const args = process.argv
if (args.includes("--help") || args.includes("-h")) { 
  constHelpObj = [
    {"param":  "--compile", "description": "read figmaLayoutDefinitions.txt and areaKeySVGMap.csv and produce charMap.json"},
    {"param":  "--verbose, -v", "description": "lots of logs"},
    {"param":  "--terse, -t", "description": "bare minimum logs"},
    {"param":  "--write, -w", "description": "write to charMap.js, without this flag, will only preview changes"},
    {"param":  "--help, -h", "description": "help!"}
  ]
  console.table(constHelpObj)
}
else if (args.includes("--compile")) {
  let verbose = false
  if (args.includes("--verbose") || args.includes("-v")) {
    verbose = true
  }
  let terse = false
  if (args.includes("--terse") || args.includes("-t")) {
    terse = true
  }
  let write = false
  if (args.includes("--write") || args.includes("-w")) {
    write = true
  }
  // #region PART 1: figmaLayouts --> figmaObj
  const figmaStr = fs.readFileSync('figmaLayoutDefinitions.txt', 'utf8');
  const figmaArr = figmaStr.split('\n');
  let figmaObj = {}
  let currLayout = null
  let currKey = null
  let currTop = null
  function figmaPercentageToPixel(line, total) {
    return Math.round(Number(line.split(": ")[1].replace("%;", "")) / 100 * total)
  }
  ctr = 0
  figmaArr.forEach((line) => {
    if (line == "")
      return

    if (line.includes("/*") && line.includes("*/") && line.includes("layout_")) {
      currLayout = line.substring(3, line.length - 3)
      console.log("layout", currLayout)
      figmaObj[currLayout] =  {}
    }

    // console.log(ctr, currLayout)
    if (line.includes("/*") && line.includes("*/") && !line.includes("area_")) {
      currKey = null
    }
    else if (line.includes("/*") && line.includes("*/") && line.includes("area_")) {
      currKey = line.substring(3, line.length - 3)
      figmaObj[currLayout][currKey] =  {"x": null, "y": null, "w": null, "h": null, "components": []}
    }


    if (currKey == null)
      return
  
    if (line.includes("area_")) {
      currKey = line.substring(3, line.length - 3)
      figmaObj[currLayout][currKey] =  {	"x": null, "y": null, "w": null, "h": null, "components": []}
    }
    else if (line.includes("left: ")) {
      if (line.includes("px;"))
        figmaObj[currLayout][currKey].x = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
      else  {
        figmaObj[currLayout][currKey].x = figmaPercentageToPixel(line, 1000)
      }
    }
    else if (line.includes("width: ")) {
      figmaObj[currLayout][currKey].w = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
    }
    else if (line.includes("right: ")) {
      figmaObj[currLayout][currKey].w = 1000 - figmaPercentageToPixel(line, 1000) - figmaObj[currLayout][currKey].x
    }
    else if (line.includes("top: ")) {
      if (line.includes("px;"))
        figmaObj[currLayout][currKey].y = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
      else 
        figmaObj[currLayout][currKey].y = figmaPercentageToPixel(line, 1000)
    }
    else if (line.includes("height: ")) {
      figmaObj[currLayout][currKey].h = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
    }
    else if (line.includes("bottom: ")) {
      figmaObj[currLayout][currKey].h = 1000 - figmaPercentageToPixel(line, 1000) - figmaObj[currLayout][currKey].y
    }
    ctr++
  })
  if (verbose)
    console.log("1. figmaObj", figmaObj) 
  else if (!terse)
    console.log("1. figmaObj", Object.keys(figmaObj))
  else
    console.log("1. figmaObj done")
  // #endregion

  // #region PART 2: areaKeySVGMap.csv > areaMap
  const csv = fs.readFileSync('areaKeySVGMap.csv', 'utf8');  
  const csvArr = csv.split('\n');
  let csvObj = []

  areaMap = {}
  let csvKeys = ["area", "keys", "filename", "width"]//csvArr[0].trim().split(",")
  csvArr.forEach((line, i) => {
    if (line == "" || i == 0)
      return
    const cells = line.split(",")
    let obj = {}
    let areas = cells[0].trim().split(";")
    areas.map((area) => {
      cells.forEach((cell, i) => {
        if (i<csvKeys.length)
          obj[csvKeys[i]] = cell.trim()
      })
      // csvObj.push(obj)
      if (areaMap[area] == undefined)
        areaMap[area] = []
      areaMap[area].push({
        "keys": obj.keys.split(";"),
        "filename": obj.filename,
        "width": Number(obj.width)
      })
    })
  })
  if (verbose)
    console.log("2. areaMap", areaMap)
  else if (!terse)
    console.log("2. areaMap", Object.keys(areaMap))
  else
    console.log("2. areaMap done")
  // #endregion

  // #region PART 3: figmaObj + areaMap > charMap
  let unicode = 58000 // start of unicode
  let unicodeDict = {}
  let charMap = {}
  // spacer
  charMap.spacer = {unicode: unicode}
  unicode++

  // glyphs
  for (let layout in figmaObj) {
    for (let area in figmaObj[layout]) {
      charMap[layout + "__" + area] = JSON.parse(JSON.stringify(figmaObj[layout][area]))
      cMLA = charMap[layout + "__" + area]
      cMLA.components = areaMap[area] ? JSON.parse(JSON.stringify(areaMap[area])) : []
      for (let i=0; i<cMLA.components.length; i++) {
        const unicodeDictKey = `${cMLA.x}_${cMLA.y}_${cMLA.w}_${cMLA.h}_${cMLA.components[i].filename}_${cMLA.components[i].width}`
        if (unicodeDict[unicodeDictKey] == undefined) {
          cMLA.components[i].unicode = unicode
          unicodeDict[unicodeDictKey] = unicode
          unicode++
        }
        else {
          cMLA.components[i].unicode = unicodeDict[unicodeDictKey]
        }
      }
    }
  }
  if (verbose)
    console.log("3. charMap", charMap)
  else if (!terse)
    console.log("3. charMap", Object.keys(charMap))
  else
    console.log("3. charMap done")
  // #endregion


  if (args.includes("--write")) {
    fs.writeFileSync("charMap.json", JSON.stringify(charMap))
    console.log("WROTE TO FILE!", "charMap.json")
  }
  else {
    console.log("Did NOT write to file.")
  }
}