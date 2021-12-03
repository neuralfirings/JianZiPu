import xml.etree.ElementTree as ET
import json

HOME_PATH = '/Users/nyl/git_projects/JianZiPu'

with open(HOME_PATH + '/src/charMap.js') as dataFile:
    data = dataFile.read()
    obj = data[data.find('{') : data.rfind('}')+1]
    charMap = json.loads(obj)

font = fontforge.open(HOME_PATH + '/src/JianZiPu.sfd')
for area in charMap:
	print("======" + area + "======")
	print(str(charMap[area]['h']) + ', ' + str(charMap[area]['w']))
	for component in charMap[area]['components']:
		print(component)

		# import
		if area == "char":
			glyph = font.createChar(fontforge.unicodeFromName(component['keys'][0]))
		else:
			glyph = font.createChar(component['unicode'])
		glyph.clear()
		glyph.importOutlines(HOME_PATH+'/src/components/' + component['filename'] + '.svg', scale=False)

		# scale to SVG
		svg = ET.parse(HOME_PATH + '/src/components/' + component['filename'] + '.svg')
		root = svg.getroot()
		svgWidth = float(root.attrib['width'].replace('px', ''))
		svgHeight = float(root.attrib['height'].replace('px', ''))
		bb = glyph.boundingBox()
		# print('bb: ' + str(svgWidth) + 'x' + str(svgHeight))
		scaleWidth = charMap[area]['w'] / svgWidth
		scaleHeight = charMap[area]['h'] / svgHeight
		if 'scale' in component.keys():
			if component['scale'] == 'lockRatio':
				scaleHeight = min(scaleHeight, scaleWidth)
				scaleWidth = min(scaleHeight, scaleWidth)

		scoochY = 800-scaleHeight*800

		# Import, scale, and scooch
		# print('scale: ' + str(scaleWidth) + ', ' + str(scaleHeight))
		glyph.transform((scaleWidth, 0.0, 0.0, scaleHeight, 0, 0)) # scaleX, skewX, skewY, scaleY, positionX, positionY
		glyph.transform((1, 0.0, 0.0, 1, 0, 800-800*scaleHeight)) # scaleX, skewX, skewY, scaleY, positionX, positionY
		glyph.transform((1, 0.0, 0.0, 1, charMap[area]['x'], -charMap[area]['y'])) # scaleX, skewX, skewY, scaleY, positionX, positionY
		
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
print('ALL DONE!')