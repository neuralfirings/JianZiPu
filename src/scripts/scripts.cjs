const fs = require('fs');

const args = process.argv

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

if (args.includes("--help") || args.includes("-h")) { 
  constHelpObj = [
    {"param":  "--compile", "description": "read figmaLayoutDefinitions.txt and areaKeySVGMap.csv and produce charMap.json & babelDict.json"},
    {"param":  "--add-positions", "description": "read layout_area_positions.json + input/fontForgeFeatures.fea and add positions to output/fontForgeFeatures.fea"},
    {"param":  "--verbose, -v", "description": "lots of logs"},
    {"param":  "--terse, -t", "description": "bare minimum logs"},
    {"param":  "--write, -w", "description": "write to charMap.json & babelDict.json, without this flag, will only preview changes"},
    {"param":  "--help, -h", "description": "help!"}
  ]
  console.table(constHelpObj)
}
else if (args.includes("--compile")) {
  // let verbose = false
  // if (args.includes("--verbose") || args.includes("-v")) {
  //   verbose = true
  // }
  // let terse = false
  // if (args.includes("--terse") || args.includes("-t")) {
  //   terse = true
  // }
  // let write = false
  // if (args.includes("--write") || args.includes("-w")) {
  //   write = true
  // }
  // #region PART 1: figmaLayouts --> layoutMap
  /**
   * output: layoutMap = {
   *   layout_xxx: {
   *     width: xxx,
   *     area_xxx: { x: xxx, y: xxx, w: xxx, h: xxx }
   *   }
   * }
   */
  const figmaStr = fs.readFileSync('../input/figma.css', 'utf8');
  const figmaArr = figmaStr.split('\n');
  let layoutMap = {}
  let currLayout = null
  let currKey = null
  let currTop = null
  function figmaPercentageToPixel(line, total) {
    return Math.round(Number(line.split(": ")[1].replace("%;", "")) / 100 * total)
  }
  ctr = 0
  let advanceWidths = {}
  figmaArr.forEach((line) => {
    if (line == "")
      return

    if (line.includes("/*") && line.includes("*/") && line.includes("layout_")) {
      currLayout = line.substring(3, line.length - 3)
      console.log("layout", currLayout)
      layoutMap[currLayout] =  {}
    }

    if (currLayout && line.includes("width: ") && layoutMap[currLayout].width == undefined) {
      const w = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
      layoutMap[currLayout].width = w
      advanceWidths[w] = undefined
    }

    // console.log(ctr, currLayout)
    if (line.includes("/*") && line.includes("*/") && !line.includes("area_")) {
      currKey = null
    }
    else if (line.includes("/*") && line.includes("*/") && line.includes("area_")) {
      currKey = line.substring(3, line.length - 3)
      layoutMap[currLayout][currKey] =  {"x": null, "y": null, "w": null, "h": null } //, "components": []}
    }


    if (currKey == null)
      return
  
    if (line.includes("area_")) {
      currKey = line.substring(3, line.length - 3)
      layoutMap[currLayout][currKey] =  {	"x": null, "y": null, "w": null, "h": null } //, "components": []}
    }
    else if (line.includes("left: ")) {
      if (line.includes("px;"))
        layoutMap[currLayout][currKey].x = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
      else  {
        layoutMap[currLayout][currKey].x = figmaPercentageToPixel(line, 1000)
      }
    }
    else if (line.includes("width: ")) {
      layoutMap[currLayout][currKey].w = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
    }
    else if (line.includes("right: ")) {
      layoutMap[currLayout][currKey].w = 1000 - figmaPercentageToPixel(line, 1000) - layoutMap[currLayout][currKey].x
    }
    else if (line.includes("top: ")) {
      if (line.includes("px;"))
        layoutMap[currLayout][currKey].y = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
      else 
        layoutMap[currLayout][currKey].y = figmaPercentageToPixel(line, 1000)
    }
    else if (line.includes("height: ")) {
      layoutMap[currLayout][currKey].h = Math.round(Number(line.split(": ")[1].replace("px", "").replace(";", "")))
    }
    else if (line.includes("bottom: ")) {
      layoutMap[currLayout][currKey].h = 1000 - figmaPercentageToPixel(line, 1000) - layoutMap[currLayout][currKey].y
    }
    ctr++
  })

  // add yd to layoutMap
  for (let layout in layoutMap) {
    for (let area in layoutMap[layout]) {
      layoutMap[layout][area].yd = 1000 - layoutMap[layout][area].y - layoutMap[layout][area].h - 200
    }
  }

  if (verbose)
    console.log("1. layoutMap", layoutMap) 
  else if (!terse)
    console.log("1. layoutMap", Object.keys(layoutMap))
  else
    console.log("1. layoutMap done")
  // #endregion

  if (false) {
    // #region layoutMap --> feature positions
    /**
     * output: positions = [ 'pos @layout_tiao3_area_right <170 -34 0 0>;' ]
     */
    let positions = []
    for (let layout in layoutMap) {
      for (let area in layoutMap[layout]) {
        if (area == "width")
          continue
        a = layoutMap[layout][area]
        positions.push(`pos @${layout}_${area} <${a.x} ${a.y-204} 0 0>;`)
        positions.push(`pos @${layout}_${area}_gou3 <${a.x} ${a.y-204} 0 0>;`)
      }
    }

    positions = positions.filter((p, i, self) => self.indexOf(p) === i)
    if (verbose)
      console.log("2. positions", positions)
    else if (!terse)
      console.log("2. positions", positions.length)
    else
      console.log("2. positions done")
    // #endregion

    // #region areaKeySVGMap.csv > areaMap (area to glyph names)
    /**
     * output: areaMap = {
     *   area_xxx: [ 'ch_xx', 'ch_xx', etc ]
     * }
     */
    const csv = fs.readFileSync('../input/areaKeySVGMap.csv', 'utf8');  
    const csvArr = csv.split('\n');
    let csvObj = []

    areaMap = {}
    let csvKeys = ["area", "keys", "filename", "width", "layouts", "translations"]//csvArr[0].trim().split(",")
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
        csvObj.push(obj)
        if (areaMap[area] == undefined)
          areaMap[area] = []
        areaMap[area].push(obj.filename)
      })
    })

    for (area in areaMap) {
      areaMap[area] = areaMap[area].filter((a, i, self) => self.indexOf(a) === i)
    }
    // areaMap.forEach((area) => {
    //   // make area (array) unique
    //   area = area.filter((a, i, self) => self.indexOf(a) === i)
    // })

    // for (let layout in layoutMap) {
    //   for (let area in layoutMap[layout]) {
    //     if (area == "width")
    //       continue
    //     layoutMap[layout][area].glyphs = areaMap[area]
    //   }
    // }
    if (verbose)
      console.log("2. areaMap", JSON.stringify(areaMap, null, 2))
    else if (!terse)
      console.log("2. areaMap", Object.keys(areaMap))
    else
      console.log("2. areaMap done")
    // #endregion

    // #region areaMap --> feature base classes
    /**
     * output: baseClasses = '@area_xxx = [ ch_xx, ch_xx, etc ];'
     */
    let baseClassesArr = []
    for (let area in areaMap) {
      baseClassesArr.push(`@area_${area} = [ ${areaMap[area].join(", ")} ];`)
    }
    // unique
    baseClassesArr = baseClassesArr.filter((a, i, self) => self.indexOf(a) === i)
    let baseClasses = baseClassesArr.join("\n")
    if (verbose)
      console.log("baseClasses", baseClasses)
    else if (!terse)
      console.log("baseClasses", baseClasses.length)
    else
      console.log("baseClasses done")
    // #endregion


    // #region PART 3: layoutMap + areaMap > charMap
    let unicode = 58000 // start of unicode
    let unicodeDict = {}
    let charMap = {}
    // spacer
    charMap.spacer = {unicode: unicode}
    unicode++
    charMap.spacers = {}
    for (let w in advanceWidths) {
      charMap.spacers[w] = {
        unicode: unicode,
        width: Number(w)
      }
      unicode++
    }

    // glyphs
    for (let layout in layoutMap) {
      const l = layout.replace("layout_", "")
      charMap[l] = {
        width: layoutMap[layout].width,
        areas: {}
      }
      for (let area in layoutMap[layout]) {
        if (area == "width")
          continue
        let a = area.replace("area_", "")
        let thisArea = JSON.parse(JSON.stringify(layoutMap[layout][area]))
        // cMLA = charMap[layout + "__" + area]
        thisArea.components = areaMap[area] ? JSON.parse(JSON.stringify(
          areaMap[area].filter((a) => a.layouts.includes(layout) || a.layouts.length == 0)
        )) : []
        // console.log("cMLA", layout, area, cMLA)
        // for (let i=0; i<thisArea.components.length; i++) {
        //   const unicodeDictKey = `${thisArea.x}_${thisArea.y}_${thisArea.w}_${thisArea.h}_${thisArea.components[i].filename}_${thisArea.components[i].width}`
        //   if (unicodeDict[unicodeDictKey] == undefined) {
        //     thisArea.components[i].unicode = unicode
        //     unicodeDict[unicodeDictKey] = unicode
        //     unicode++
        //   }
        //   else {
        //     thisArea.components[i].unicode = unicodeDict[unicodeDictKey]
        //   }
        // }
        charMap[l].areas[a] = thisArea
      }
    }
    if (verbose)
      console.log("3. charMap", JSON.stringify(charMap, null, 2))
    else if (!terse)
      console.log("3. charMap", Object.keys(charMap))
    else
      console.log("3. charMap done")
    // #endregion

    // #region PART 4: areaKeySVGMap.csv > babelDict
    let babelDictStr = []
    csvObj.forEach((obj) => {
      const translations = obj.translations.split(";").filter((t) => t != "")
      const keys = obj.keys.split(";").filter((k) => k != "")
      keys.map(k => {
        let obj = { "key": k, "translation": k }
        let str = JSON.stringify(obj)
        if (!babelDictStr.includes(str)) babelDictStr.push(str)
      
        translations.map((t) => {
          obj = { "key": k, "translation": t }
          str = JSON.stringify(obj)
          if (!babelDictStr.includes(str)) babelDictStr.push(str)
        })
      })
    })
    let babelDict = babelDictStr.map((str) => JSON.parse(str))
    // babelDict = babelDict.sort((a, b) => b.translations.length - a.translations.length)
    if (verbose)
      console.log("4. babelDict", babelDict)
    else
      console.log("4. babelDict done")
    // #endregion


  }

  if (write == true) {
    // START HERE
    // look through .fea file, and slowly build this file, @base, @layout_blah, positions (done), etc.
    // also do ligatures
    // not sure about how to handle Cuo, Verts, U, and ju/ki/lo 
    layoutAreaFilename = "../output/layout_area_positions.json"
    fs.writeFileSync(layoutAreaFilename, JSON.stringify(layoutMap))
    console.log("WROTE TO FILE!", layoutAreaFilename)

    // positionsFileName = "../output/jzpFeatures.fea"
    // fs.writeFileSync(positionsFileName, "#region base classes\n" + baseClasses + "\n#endregion base classes\n\n" + "#region positions\n" + positions.join("\n") + "\n#endregion positions")
    // console.log("WROTE TO FILE!", positionsFileName)
    // fs.writeFileSync("charMap.json", JSON.stringify(charMap))
    // fs.writeFileSync("babelDict.json", JSON.stringify(babelDict))
    // console.log("WROTE TO FILE!", "charMap.json", "babelDict.json")
  }
  else {
    console.log("Did NOT write to file.")
  }
}
else if (args.includes("--add-positions")) {
  const positionsObj = JSON.parse(fs.readFileSync("../output/layout_area_positions.json", "utf8"));
  const positions = []
  for (let layout in positionsObj) {
    let thisLayoutArr = {
      layout: layout,
      areas: []
    }
    for (let area in positionsObj[layout]) {
      thisLayoutArr.areas.push({
        area: area,
        ...positionsObj[layout][area]
      })
    }
    positions.push(thisLayoutArr)
  }
  
  let input = fs.readFileSync("../input/fontForgeFeatures.fea", "utf8");
  // const output = fs.readFileSync("../output/fontForgeFeatures.fea", "utf8");

  // chinese to glyph names
  let renameCSV = fs.readFileSync("../input/fontForgeGlyphRename.csv", "utf8");
  const renameCSVArr = renameCSV.split("\n");
  const header = renameCSVArr[0].split(",").map(h => h.trim())
  const c2gDict = renameCSVArr
    .map(line => {
      const lineArr = line.split(",");
      const obj = {};
      header.forEach((h, i) => {
        obj[h] = lineArr[i].trim();
      });
      return obj;
    })
    .filter(d => d.new_glyph_name != "" && d.unicode_value >= 12290 && d.unicode_value <= 65372)
    .map(d => ({ch: d.unicode_char, name: d.new_glyph_name}))

  // console.log("c2gDict", c2gDict)
  c2gDict.forEach(d => {
    input = input.replaceAll(d.ch, d.name)
  })
  
  // JZP_POSITION_TEMPLATE --> individual jzp layouts
  const jzpPositionTemplate = input.split("# JZP_POSITION_MEGA_SECTION")[1].split("# JZP_POSITION_MEGA_SECTION")[0]
  const rightKeys = ['loki', 'nc', 'tiao', 'mo', 'gou', 'io']
  const jzpPositions = rightKeys.map((rightKey) => jzpPositionTemplate.replaceAll("xx", rightKey))

  input = input.replace(jzpPositionTemplate, jzpPositions.join(""))
  
// add positions
  const feaArr = input.split("\n");
  let currLayout = null
  feaArr.forEach((line, i) => {
    if (line.trim()[0] == "#" && line.includes("layout: ")) {
      currLayout = line.substring(line.indexOf("layout: ") + 7, line.length).trim()
      console.log("Processing layout:", currLayout)
    }
    else if (line.trim().startsWith("#")) {
      return 
    }
    // if (currLayout == null)
    //   return

    if (currLayout != null) {
      positions.forEach((layout) => {
        // console.log("match?", currLayout == layout.layout, currLayout, layout.layout)
        if (layout.layout != currLayout) return
        // console.log("Found layout:", layout)
        layout.areas.forEach((area) => {
          const words = line.split(' ')
          words.forEach((word, wIdx) => {
            if (word.split('__')[0].split("'")[0] == '@' + area.area 
              && word.at(-1) == "'" 
              && words[wIdx+1].startsWith("<>"))
            {
              words[wIdx + 1] = words[wIdx + 1].replace("<>", `<${area.x} ${area.yd} 0 0>`)
            }
          })
          line = words.join(' ')
        })
      })
    }

    // replace @area_foo[3->0] with 4 lines going from @area_foo @area_foo @area_foo to nothing
    if (line.includes("[") && line.includes("->") && line.includes("]")) {
      const wordToReplace = line.split(" ").filter(w => w.includes('['))[0]
      const [area, temp] = wordToReplace.split("[")
      const [max, temp2] = temp.split("->")
      const [min, temp3] = temp2.split("]")
      console.log("wordToReplace", wordToReplace, area, max, min)

      const newLines = []
      for (let i = Number(max); i >= Number(min); i--) {
        newLines.push(line.replace(`${wordToReplace} `, `${area} `.repeat(i)))
      }
      line = newLines.join("\n")
    }
    feaArr[i] = line
  });

  if (write == true) {
    fs.writeFileSync("../output/fontForgeFeatures.fea", feaArr.join("\n"))
    console.log("WROTE TO FILE!", "../output/fontForgeFeatures.fea")
  }
  else {
    console.log("Did NOT write to file.")
  }
}

function truncateAfterDoubleUnderscore(str) {
  return str.split(' ').map(word => {
    const doubleUnderscoreIndex = word.indexOf('__');
    if (doubleUnderscoreIndex !== -1) {
      return word.substring(0, doubleUnderscoreIndex);
    }
    return word;
  }).join(' ');
}