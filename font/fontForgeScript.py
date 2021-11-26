import xml.etree.ElementTree as ET

charMap = {
	"char": { "x": 0, "y": 0, "w": 1000, "h": 1000, "components": [
		{ "key": "c", "filename":"c_qiaqi_l", "unicode": 58000, "width": 1000},
		{ "key": "d", "filename":"d_zhong_l", "unicode": 58001, "width": 1000},
		{ "key": "f", "filename":"f_index_l", "unicode": 58002, "width": 1000},
		{ "key": "H", "filename":"H_cuo_l", "unicode": 58003, "width": 1000},
		{ "key": "h", "filename":"h_tuo_l", "unicode": 58004, "width": 1000},
		{ "key": "I", "filename":"I_dacuo_l", "unicode": 58005, "width": 1000},
		{ "key": "i", "filename":"i_ti_l", "unicode": 58006, "width": 1000},
		{ "key": "j", "filename":"j_mo_l", "unicode": 58007, "width": 1000},
		{ "key": "k", "filename":"k_gou_l", "unicode": 58008, "width": 1000},
		{ "key": "l", "filename":"l_da_l", "unicode": 58009, "width": 1000},
		{ "key": "n", "filename":"n_bo_l", "unicode": 58010, "width": 1000},
		{ "key": "O", "filename":"O_fancuo_l", "unicode": 58011, "width": 1000},
		{ "key": "o", "filename":"o_zhai_l", "unicode": 58012, "width": 1000},
		{ "key": "s", "filename":"s_ming_l", "unicode": 58013, "width": 1000},
		{ "key": "Y", "filename":"Y_fancuo_l", "unicode": 58014, "width": 1000},
		{ "key": "u", "filename":"u_tiao_l", "unicode": 58015, "width": 1000},
		{ "key": "v", "filename":"v_da_l", "unicode": 58016, "width": 1000},
		{ "key": "V", "filename":"V_yan_l", "unicode": 58017, "width": 1000},
		{ "key": "x", "filename":"x_gui_l", "unicode": 58018, "width": 1000},
		{ "key": "U", "filename":"U_li_m", "unicode": 58019, "width": 1000},
	]},
	"rhFull": { "x": 100, "y": 100, "w": 800, "h": 800, "components": [
		{ "key": "n", "filename": "n_bo_l", "unicode": 58020, "width": 0 },
		{ "key": "h", "filename": "h_tuo_l", "unicode": 58021, "width": 0 },
		{ "key": "u", "filename": "u_tiao_l", "unicode": 58022, "width": 0 },
		{ "key": "k", "filename": "k_gou_l", "unicode": 58023, "width": 0 },
		{ "key": "i", "filename": "i_ti_l", "unicode": 58024, "width": 0 },
		{ "key": "l", "filename": "l_da_l", "unicode": 58025, "width": 0 },
		{ "key": "o", "filename": "o_zhai_l", "unicode": 58026, "width": 0 },
		{ "key": "c", "filename": "c_qiaqi_l", "unicode": 58027, "width": 0 },
		{ "key": "U", "filename": "U_li_m", "unicode": 58028, "width": 0 }
	]},
	"strFull": { "x": 200, "y": 200, "w": 600, "h": 600, "components": [
		{ "key": "1", "filename": "1_yi_l", "unicode": 58029, "width": 0 },
		{ "key": "2", "filename": "2_er_l", "unicode": 58030, "width": 0 },
		{ "key": "3", "filename": "3_san_l", "unicode": 58031, "width": 0 },
		{ "key": "4", "filename": "4_si_l", "unicode": 58032, "width": 0 },
		{ "key": "5", "filename": "5_wu_l", "unicode": 58033, "width": 0 },
		{ "key": "6", "filename": "6_liu_l", "unicode": 58034, "width": 0 },
		{ "key": "7", "filename": "7_qi_l", "unicode": 58035, "width": 0 }
	]},
	"strFullTop": { "x": 355, "y": 200, "w": 290, "h": 290, "components": [
		{ "key": "1", "filename": "1_yi_l", "unicode": 58036, "width": 0 },
		{ "key": "2", "filename": "2_er_l", "unicode": 58037, "width": 0 },
		{ "key": "3", "filename": "3_san_l", "unicode": 58038, "width": 0 },
		{ "key": "4", "filename": "4_si_l", "unicode": 58039, "width": 0 },
		{ "key": "5", "filename": "5_wu_l", "unicode": 58040, "width": 0 },
		{ "key": "6", "filename": "6_liu_l", "unicode": 58041, "width": 0 },
		{ "key": "7", "filename": "7_qi_l", "unicode": 58042, "width": 0 }
	]},
	"strFullTop": { "x": 355, "y": 510, "w": 290, "h": 290, "components": [
		{ "key": "1", "filename": "1_yi_l", "unicode": 58043, "width": 0 },
		{ "key": "2", "filename": "2_er_l", "unicode": 58044, "width": 0 },
		{ "key": "3", "filename": "3_san_l", "unicode": 58045, "width": 0 },
		{ "key": "4", "filename": "4_si_l", "unicode": 58046, "width": 0 },
		{ "key": "5", "filename": "5_wu_l", "unicode": 58047, "width": 0 },
		{ "key": "6", "filename": "6_liu_l", "unicode": 58048, "width": 0 },
		{ "key": "7", "filename": "7_qi_l", "unicode": 58049, "width": 0 }
	]},
	"lhHalf": { "x": 100, "y": 100, "w": 374, "h": 305, "components": [
		{ "key": "v", "filename": "v_da_s", "unicode": 58050, "width": 0},
		{ "key": "f", "filename": "f_index_s", "unicode": 58051, "width": 0},
		{ "key": "d", "filename": "d_zhong_s", "unicode": 58052, "width": 0},
		{ "key": "s", "filename": "s_ming_s", "unicode": 58053, "width": 0},
		{ "key": "x", "filename": "x_gui_s", "unicode": 58054, "width": 0},
	]},
	"huiHalf": { "x": 500, "y": 100, "w": 400, "h": 305, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58055, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58056, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58057, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58058, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58059, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58060, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58061, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58062, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58063, "width": 0 },
		{ "key": "10", "filename": "10_shi_s", "unicode": 58064, "width": 0 },
	]},
	"huiHalfTop": { "x": 500, "y": 100, "w": 400, "h": 150, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58065, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58066, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58067, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58068, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58069, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58070, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58071, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58072, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58073, "width": 0 },
		{ "key": "10", "filename": "10_shi_s", "unicode": 58074, "width": 0 },
		{ "key": "11", "filename": "11_s", "unicode": 58075, "width": 0 },
		{ "key": "12", "filename": "12_s", "unicode": 58076, "width": 0 },
		{ "key": "13", "filename": "13_s", "unicode": 58077, "width": 0 },
	]},
	"huiHalfBottom": { "x": 500, "y": 255, "w": 400, "h": 150, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58078, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58079, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58080, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58081, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58082, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58083, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58084, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58085, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58086, "width": 0 }
	]},
	"rhHalf": { "x": 100, "y": 431, "w": 800, "h": 469, "components": [
		{ "key": "n", "filename": "n_bo_m", "unicode": 58087, "width": 0 },
		{ "key": "h", "filename": "h_tuo_m", "unicode": 58088, "width": 0 },
		{ "key": "u", "filename": "u_tiao_m", "unicode": 58089, "width": 0 },
		{ "key": "k", "filename": "k_gou_m", "unicode": 58090, "width": 0 },
		{ "key": "i", "filename": "i_ti_m", "unicode": 58091, "width": 0 },
		{ "key": "l", "filename": "l_da_m", "unicode": 58092, "width": 0 },
		{ "key": "o", "filename": "o_zhai_m", "unicode": 58093, "width": 0 },
		{ "key": "c", "filename": "c_qiaqi_m", "unicode": 58094, "width": 0 },
		{ "key": "U", "filename": "U_li_m", "unicode": 58095, "width": 0 },
	]},
	"strHalf": { "x": 245, "y": 540, "w": 520, "h": 230 , "components": [
		{ "key": "1", "filename": "1_yi_m", "unicode": 58096, "width": 0 },
		{ "key": "2", "filename": "2_er_m", "unicode": 58097, "width": 0 },
		{ "key": "3", "filename": "3_san_m", "unicode": 58098, "width": 0 },
		{ "key": "4", "filename": "4_si_m", "unicode": 58099, "width": 0 },
		{ "key": "5", "filename": "5_wu_m", "unicode": 58100, "width": 0 },
		{ "key": "6", "filename": "6_liu_m", "unicode": 58101, "width": 0 },
		{ "key": "7", "filename": "7_qi_m", "unicode": 58102, "width": 0 }
	]},
	"strHalfTop": { "x": 300, "y": 480, "w": 385, "h": 200 , "components": [
		{ "key": "1", "filename": "1_yi_m", "unicode": 58103, "width": 0 },
		{ "key": "2", "filename": "2_er_m", "unicode": 58104, "width": 0 },
		{ "key": "3", "filename": "3_san_m", "unicode": 58105, "width": 0 },
		{ "key": "4", "filename": "4_si_m", "unicode": 58106, "width": 0 },
		{ "key": "5", "filename": "5_wu_m", "unicode": 58107, "width": 0 },
		{ "key": "6", "filename": "6_liu_m", "unicode": 58108, "width": 0 },
		{ "key": "7", "filename": "7_qi_m", "unicode": 58109, "width": 0 }
	]},
	"strHalfBottom": { "x": 300, "y": 700, "w": 385, "h": 200 , "components": [
		{ "key": "1", "filename": "1_yi_m", "unicode": 58110, "width": 0 },
		{ "key": "2", "filename": "2_er_m", "unicode": 58111, "width": 0 },
		{ "key": "3", "filename": "3_san_m", "unicode": 58112, "width": 0 },
		{ "key": "4", "filename": "4_si_m", "unicode": 58113, "width": 0 },
		{ "key": "5", "filename": "5_wu_m", "unicode": 58114, "width": 0 },
		{ "key": "6", "filename": "6_liu_m", "unicode": 58115, "width": 0 },
		{ "key": "7", "filename": "7_qi_m", "unicode": 58116, "width": 0 }
	]},
	"thirdMidFull": { "x": 300, "y": 420, "w": 400, "h": 240, "components": [
		{ "key": "j", "filename": "j_mo_s", "unicode": 58117, "width": 0 },
		{ "key": "V", "filename": "V_yan_s", "unicode": 58118, "width": 0 },
		{ "key": "0", "filename": "0_san_m", "unicode": 58119, "width": 0 }
	]},
	"thirdMidLeft": { "x": 260, "y": 420, "w": 230, "h": 230, "components": [
		{ "key": "v", "filename": "v_da_s", "unicode": 58120, "width": 0},
		{ "key": "f", "filename": "f_index_s", "unicode": 58121, "width": 0},
		{ "key": "d", "filename": "d_zhong_s", "unicode": 58122, "width": 0},
		{ "key": "s", "filename": "s_ming_s", "unicode": 58123, "width": 0},
		{ "key": "x", "filename": "x_gui_s", "unicode": 58124, "width": 0}
	]},
	"thirdMidRight": { "x": 500, "y": 420, "w": 230, "h": 230, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58125, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58126, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58127, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58128, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58129, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58130, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58131, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58132, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58133, "width": 0 },
		{ "key": "10", "filename": "10_shi_s", "unicode": 58134, "width": 0 },
		{ "key": "11", "filename": "11_s", "unicode": 58135, "width": 0 },
		{ "key": "12", "filename": "12_s", "unicode": 58136, "width": 0 },
		{ "key": "13", "filename": "13_s", "unicode": 58137, "width": 0 },
	]},
	"rhThirdBottom": { "x": 100, "y": 660, "w": 800, "h": 305, "components": [
		{ "key": "n", "filename": "n_bo_m", "unicode": 58138, "width": 0 },
		{ "key": "h", "filename": "h_tuo_m", "unicode": 58139, "width": 0 },
		{ "key": "u", "filename": "u_tiao_m", "unicode": 58140, "width": 0 },
		{ "key": "k", "filename": "k_gou_m", "unicode": 58141, "width": 0 },
		{ "key": "i", "filename": "i_ti_m", "unicode": 58142, "width": 0 },
		{ "key": "l", "filename": "l_da_m", "unicode": 58143, "width": 0 },
		{ "key": "o", "filename": "o_zhai_m", "unicode": 58144, "width": 0 }
	]},
	"strThird": { "x": 230, "y": 690, "w": 540, "h": 250, "components": [
		{ "key": "1", "filename": "1_yi_l", "unicode": 58145, "width": 0 },
		{ "key": "2", "filename": "2_er_l", "unicode": 58146, "width": 0 },
		{ "key": "3", "filename": "3_san_l", "unicode": 58147, "width": 0 },
		{ "key": "4", "filename": "4_si_l", "unicode": 58148, "width": 0 },
		{ "key": "5", "filename": "5_wu_l", "unicode": 58149, "width": 0 },
		{ "key": "6", "filename": "6_liu_l", "unicode": 58150, "width": 0 },
		{ "key": "7", "filename": "7_qi_l", "unicode": 58151, "width": 0 }
	]},
	"halfUpper": { "x": 373, "y": 373, "w": 260, "h": 145, "components": [
		{ "key": "/", "filename": "fwdSlash_shang_s", "unicode": 58152, "width": 0 }
	]},
	"halfLeft": { "x": 0, "y": 430, "w": 100, "h": 500, "components": [
		{ "key": "\\", "filename": "bckSlash_xia_m", "unicode": 58153, "width": 0 }
	]},
	"huiHalfFull": { "x": 100, "y": 100, "w": 800, "h": 305, "components": [
		{ "key": "0", "filename": "0_san_m", "unicode": 58154, "width": 0 }
	]},
	"cuo": { "x": 450, "y": -175, "w": 825, "h": 1175, "components": [
		{ "key": "H", "filename": "H_cuo_m", "unicode": 58155, "width": 667 },
		{ "key": "Y", "filename": "Y_fancuo_m", "unicode": 58156, "width": 667 },
		{ "key": "I", "filename": "I_dacuo_m", "unicode": 58157, "width": 667 },
		{ "key": "O", "filename": "O_dafancuo_m", "unicode": 58158, "width": 667 },
	]},
	"thirdMidRightTop": { "x": 500, "y": 420, "w": 230, "h": 112, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58159, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58160, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58161, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58162, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58163, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58164, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58165, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58166, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58167, "width": 0 },
		{ "key": "10", "filename": "10_shi_s", "unicode": 58168, "width": 0 },
		{ "key": "11", "filename": "11_s", "unicode": 58169, "width": 0 },
		{ "key": "12", "filename": "12_s", "unicode": 58170, "width": 0 },
		{ "key": "13", "filename": "13_s", "unicode": 58171, "width": 0 },
	]},
	"thirdMidRightBottom": { "x": 500, "y": 538, "w": 230, "h": 112, "components": [
		{ "key": "1", "filename": "1_yi_s", "unicode": 58172, "width": 0 },
		{ "key": "2", "filename": "2_er_s", "unicode": 58173, "width": 0 },
		{ "key": "3", "filename": "3_san_s", "unicode": 58174, "width": 0 },
		{ "key": "4", "filename": "4_si_s", "unicode": 58175, "width": 0 },
		{ "key": "5", "filename": "5_wu_s", "unicode": 58176, "width": 0 },
		{ "key": "6", "filename": "6_liu_s", "unicode": 58177, "width": 0 },
		{ "key": "7", "filename": "7_qi_s", "unicode": 58178, "width": 0 },
		{ "key": "8", "filename": "8_ba_s", "unicode": 58179, "width": 0 },
		{ "key": "9", "filename": "9_jiu_s", "unicode": 58180, "width": 0 },
	]},
}
font = fontforge.open('/Users/nyl/git_projects/JianZiPu/font/JianZiPu.v12.sfd')

for area in charMap:
	print("======" + area + "======")
	print(str(charMap[area]['h']) + ', ' + str(charMap[area]['w']))
	for component in charMap[area]['components']:
		print(component)

		# import
		if area == "char":
			glyph = font.createChar(fontforge.unicodeFromName(component['key']))
		else:
			glyph = font.createChar(component['unicode'])
		glyph.clear()
		glyph.importOutlines('/Users/nyl/git_projects/JianZiPu/components/' + component['filename'] + '.svg', scale=False)

		# scale to SVG
		svg = ET.parse('/Users/nyl/git_projects/JianZiPu/components/' + component['filename'] + '.svg')
		root = svg.getroot()
		svgWidth = float(root.attrib['width'].replace('px', ''))
		svgHeight = float(root.attrib['height'].replace('px', ''))
		bb = glyph.boundingBox()
		print('bb: ' + str(svgWidth) + 'x' + str(svgHeight))
		scaleWidth = charMap[area]['w'] / svgWidth
		scaleHeight = charMap[area]['h'] / svgHeight
		if 'scale' in component.keys():
			if component['scale'] == 'lockRatio':
				scaleHeight = min(scaleHeight, scaleWidth)
				scaleWidth = min(scaleHeight, scaleWidth)

		scoochY = 800-scaleHeight*800

		# Import, scale, and scooch
		print('scale: ' + str(scaleWidth) + ', ' + str(scaleHeight))
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
			glyph.glyphname = component['key']
		else:
			glyph.glyphname = 'u' + str(component['unicode'])
		print('done with: ' + glyph.glyphname)