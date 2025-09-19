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

  console.log("c2gDict", c2gDict)
  
  // const c2gDict = [
  //   {"ch":"一","name":"ch_1"},{"ch":"七","name":"ch_7"},{"ch":"三","name":"ch_3"},{"ch":"上","name":"ch_shang"},{"ch":"下","name":"ch_xia"},{"ch":"中","name":"ch_d"},{"ch":"九","name":"ch_9"},{"ch":"二","name":"ch_2"},{"ch":"五","name":"ch_5"},{"ch":"全","name":"ch_quan"},{"ch":"八","name":"ch_8"},{"ch":"六","name":"ch_6"},{"ch":"分","name":"ch_fen"},{"ch":"剌","name":"ch_la"},{"ch":"剔","name":"ch_i"},{"ch":"劈","name":"ch_n"},{"ch":"勾","name":"ch_k"},{"ch":"十","name":"ch_10"},{"ch":"半","name":"ch_ban"},{"ch":"双","name":"ch_shuang"},{"ch":"反","name":"ch_fan3"},{"ch":"叠","name":"ch_die"},{"ch":"合","name":"ch_he"},{"ch":"名","name":"ch_s"},{"ch":"吟","name":"ch_yin2"},{"ch":"四","name":"ch_4"},{"ch":"圆","name":"ch_yuan"},{"ch":"圓","name":"ch_yuan_trad"},{"ch":"外","name":"ch_wai"},{"ch":"大","name":"ch_v"},{"ch":"如","name":"ch_ru"},{"ch":"定","name":"ch_ding"},{"ch":"对","name":"ch_dui"},{"ch":"對","name":"ch_dui_trad"},{"ch":"小","name":"ch_xiao"},{"ch":"少","name":"ch_shao"},{"ch":"就","name":"ch_jiu"},{"ch":"带","name":"ch_dai"},{"ch":"帶","name":"ch_dai_trad"},{"ch":"应","name":"ch_ying"},{"ch":"开","name":"ch_kai"},{"ch":"弹","name":"ch_dan"},{"ch":"彈","name":"ch_dan_trad"},{"ch":"復","name":"ch_fu4"},{"ch":"急","name":"ch_ji"},{"ch":"息","name":"ch_xi1"},{"ch":"應","name":"ch_ying_trad"},{"ch":"打","name":"ch_l"},{"ch":"托","name":"ch_h"},{"ch":"扶","name":"ch_fu2"},{"ch":"抓","name":"ch_zhua"},{"ch":"抹","name":"ch_j"},{"ch":"拨","name":"ch_bo"},{"ch":"挑","name":"ch_u"},{"ch":"掐","name":"ch_qia"},{"ch":"掩","name":"ch_yan"},{"ch":"搂","name":"ch_lou"},{"ch":"摘","name":"ch_o"},{"ch":"摟","name":"ch_lou_trad"},{"ch":"撇","name":"ch_pie"},{"ch":"撞","name":"ch_zhuang"},{"ch":"撥","name":"ch_bo_trad"},{"ch":"撮","name":"ch_cuo"},{"ch":"散","name":"ch_san"},{"ch":"沸","name":"ch_fei"},{"ch":"泛","name":"ch_fan4"},{"ch":"注","name":"ch_zhu"},{"ch":"滚","name":"ch_gun"},{"ch":"滾","name":"ch_gun_trad"},{"ch":"猱","name":"ch_nao"},{"ch":"璅","name":"ch_suo"},{"ch":"疊","name":"ch_die_trad"},{"ch":"短","name":"ch_duan"},{"ch":"細","name":"ch_xi4_trad"},{"ch":"綽","name":"ch_chuo_trad"},{"ch":"细","name":"ch_xi4"},{"ch":"绰","name":"ch_chuo"},{"ch":"背","name":"ch_bei"},{"ch":"至","name":"ch_zhi4"},{"ch":"蠲","name":"ch_juan"},{"ch":"註","name":"ch_zhu_trad"},{"ch":"起","name":"ch_qi"},{"ch":"跪","name":"ch_x"},{"ch":"輪","name":"ch_lun_trad"},{"ch":"轮","name":"ch_lun"},{"ch":"进","name":"ch_jin"},{"ch":"退","name":"ch_tui"},{"ch":"進","name":"ch_jin_trad"},{"ch":"長","name":"ch_zhang_trad"},{"ch":"长","name":"ch_zhang"},{"ch":"開","name":"ch_kai_trad"},{"ch":"雙","name":"ch_shuang_trad"},{"ch":"音","name":"ch_yin1"},{"ch":"食","name":"ch_f"}
  // ]

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
    if (currLayout == null)
      return

    positions.forEach((layout) => {
      // console.log("match?", currLayout == layout.layout, currLayout, layout.layout)
      if (layout.layout != currLayout) return
      // console.log("Found layout:", layout)
      layout.areas.forEach((area) => {
        const words = line.split(' ')
        // console.log("words", words)
        words.forEach((word, wIdx) => {
          if (word.split('__')[0].split("'")[0] == '@' + area.area 
            && word.at(-1) == "'" 
            && words[wIdx+1].startsWith("<>"))
          {
            words[wIdx + 1] = words[wIdx + 1].replace("<>", `<${area.x} ${area.yd} 0 0>`)
            // console.log("- Adding position info:", word, words[wIdx + 1])
          }
        })
        line = words.join(' ')
        // if (truncateAfterDoubleUnderscore(line).includes(`${area.area}' <>`)) {
        //   console.log("Replacing:", `${area.area}' <>`, `${area.area}' <${area.x} ${area.yd} 0 0>`)
        //   line = line.replaceAll(`${area.area}' <>`, `${area.area}' <${area.x} ${area.yd} 0 0>`)
        // }
      })
    })
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