import codecs
import xml.etree.ElementTree as ET
import json
import os

# Get the current font, set HOME_PATH and FILE_NAME
current_font = fontforge.activeFont()
if current_font is not None:
    file_path = current_font.path
    if file_path is not None:
        HOME_PATH = os.path.dirname(file_path)
        FILE_NAME = os.path.basename(file_path)
    else:
        print("No file is currently open.")
else:
    print("No active font found.")

with codecs.open(HOME_PATH + '/charMap.json', 'r', 'utf-8') as dataFile:
    data = dataFile.read()
    obj = data[data.find('{') : data.rfind('}')+1]
    charMap = json.loads(obj)
    
font = fontforge.open(HOME_PATH + '/' + FILE_NAME)
unicodes = []
for area in charMap:
  if area == "spacer":
    glyph = font.createChar(charMap[area]['unicode'])
    glyph.clear()
    glyph.width = 1000
    glyph.glyphname = 'spacer_' + str(charMap[area]['unicode'])
    continue

  print("======" + area + "======")
  print(str(charMap[area]['h']) + ', ' + str(charMap[area]['w']))
  for component in charMap[area]['components']:
    # print(component) # note: this errors out for some reason
    # check if component is already in font
    if component['unicode'] in unicodes:
      print('Already in font')
      continue

    # handle case of using characters instead of custom unicode
    if area == "char":
      glyph = font.createChar(fontforge.unicodeFromName(component['keys'][0]))
    else:
      glyph = font.createChar(component['unicode'])
    glyph.clear()
    
    if component['filename'] != 'empty':
      # import SVG
      fp = HOME_PATH+'/components/' + component['filename'] + '.svg'
      glyph.importOutlines(fp, scale=False)
      

      # scale to SVG
      svg = ET.parse(fp)
      root = svg.getroot()
      svgWidth = float(root.attrib['width'].replace('px', ''))
      svgHeight = float(root.attrib['height'].replace('px', ''))
      bb = glyph.boundingBox()
      scaleWidth = charMap[area]['w'] / svgWidth
      scaleHeight = charMap[area]['h'] / svgHeight
      if 'scale' in component.keys():
        if component['scale'] == 'lockRatio':
          scaleHeight = min(scaleHeight, scaleWidth)
          scaleWidth = min(scaleHeight, scaleWidth)

      scoochY = 800-scaleHeight*800

      # Import, scale, and scooch
      glyph.transform((scaleWidth, 0.0, 0.0, scaleHeight, 0, 0)) # scaleX, skewX, skewY, scaleY, positionX, positionY
      glyph.transform((1, 0.0, 0.0, 1, 0, 800-800*scaleHeight)) 
      glyph.transform((1, 0.0, 0.0, 1, charMap[area]['x'], -charMap[area]['y'])) 
      
      # Clean up
      glyph.removeOverlap()
      glyph.addExtrema()

    # Change widths
    if area == "char":
      glyph.width = component['width']
    else:
      glyph.width = component['width']

    # Rename
    if area == "char":
      glyph.glyphname = component['keys'][0]
    else:
      glyph.glyphname = 'u' + str(component['unicode'])
    
    # add to unicodes array
    unicodes.append(component['unicode'])
print('ALL DONE!')