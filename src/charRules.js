const rgxRh = 
	"n|擘|擘|"+
	"h|托|托|"+
	"u|挑|挑|"+
	"ki|勾剔|勾剔|"+
	"k|勾|勾|"+
	"i|剔|剔|"+
	"l|打|打|"+
	"o|摘|摘|"+
	"c|掐起|掐起|"+
	"U|L|历|歷"
const rgxRhThirdBottom = 
	"lo|打摘|打摘"
const rgxLh = 
	"s|名|名|"+
	"d|中|中|"+
	"f|食|食|"+
	"v|大|大|"+
	"x|跪|跪"
const rgxChords = 
	"Y|FC|反撮|反撮|"+
	"I|DC|大撮|大撮|"+
	"O|DFC|大反撮|大反撮|"+
	"H|C|撮|撮|"+
	"TTT|三弹|三彈|"+
	"TT|双弹|雙彈|"+
	"BL|泼刺|潑刺|"+
	"B|泼|潑|"+
	"L|刺|刺"
const rgxMid = 
	"j|抹|抹|"+
	"V|X|罨|掩|罨|掩|"+
	"GF|滚沸|滾沸|"+
	"G|滚|滾|"+
	"F|沸|沸|"+
	"D|到|到"
const rgxModUpper = 
	"\\/|绰|綽|"+
	"\\>|急|急"
const rgxModLeft = 
	"\\\\|注|注"

const charRules = {
	for: /.*/,
	do: [
		// characters
		{ if: /退|退/, area: 'chineseChar' },
		{ if: /进|進/, use: '进', area: 'chineseChar' },
		{ if: /长吟|長吟/, use: '长吟', area: 'chineseChar' },
		{ if: /细吟|細吟/, area: 'chineseChar' },
		{ if: /分开|分開/, area: 'chineseChar' },
		{ if: /泛止|泛止/, area: 'chineseChar' },
		{ if: /大息|大息/, area: 'chineseChar' },
		{ if: /少息|少息/, area: 'chineseChar' },
		{ if: /復|復/, area: 'chineseChar' },
		{ if: /起|起/, area: 'chineseChar' },
		{ if: /泛起|泛起/, area: 'chineseChar' },
		{ if: /带起|帶起/, area: 'chineseChar' },
		{ if: /对起|對起/, area: 'chineseChar' },
		{ if: /爪起|爪起/, area: 'chineseChar' },
		{ if: /撇起|撇起/, area: 'chineseChar' },
		{ if: /打圆|打圓/, area: 'chineseChar' },
		{ if: /撞|撞/, area: 'chineseChar' },
		{ if: /散|散/, area: 'chineseChar' },
		{ if: /如|如/, area: 'chineseChar' },
		{ if: /外|外/, area: 'chineseChar' },

		// full jzp
		{ if: /[0-9]/, area: 'strFull'},
		{ if: new RegExp(`(${rgxRhThirdBottom})|(${rgxRh})|(${rgxMid})`), area: 'rhFull'},
		{ if: new RegExp(rgxModUpper), area: 'fullUpper' },
		{ if: new RegExp(rgxModLeft), area: 'fullLeft'  },

		// halves
		{ if: /\(\d.*\)/, 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: new RegExp(rgxRh), area: 'rhHalf'},
				{ if: new RegExp(rgxRhThirdBottom), area: 'rhThirdBottom', 
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'}
					]
				},
			]
		},
		{
			if: new RegExp("\\(\\d.*\\)|(" + rgxLh + ")"), 
			for: /.*/,
			do: [
				{ if: new RegExp(rgxModUpper), area: 'halfUpper' },
				{ if: new RegExp(rgxModLeft), area: 'halfLeft'  },
			]
		},
		{ if: new RegExp(rgxLh), area: 'lhHalf',
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: new RegExp(rgxRh), area: 'rhHalf'},
				{ if: new RegExp(rgxRhThirdBottom), area: 'rhThirdBottom', 
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'}
					]
				},
			]
		},
		{ if: /\(\d+\)/,
			for: /\(\d+\)/,
			do: [
				{ if: /\(\d.*\)/, remove: ['(', ')'], area: 'huiHalf' } 
			]
		},
		{ if: /\(.*\..\)/, 
			for: /\(.*\..\)/,
			do: [
				{ if: /\(\d.*\./, remove: ['(', '.'], area: 'huiHalfTop' },
				{ if: /\.\d.*\)/, remove: [')', '.'], area: 'huiHalfBottom',  },
			]
		},
		{ if: /\(0\)/, 
			for: /\(0\)/,
			do: [
				{ if: /0/, area: 'huiHalfFull'}
			]
		},
		{ if: /\(13\.\d\)/,  area: 'huiHalf',
			for: /\(13\.\d\)/,
			do: [
				{ if: /13\.\d/, use: '13.1', area: 'huiHalf'}
			]
		},

		// li
		{ if: /[0-9],[0-9]/, 
			for: /[0-9],[0-9]/,
			do: [
				{ if: /\d.*\,/, remove: [','], area: 'strHalfTop' },
				{ if: /\,\d.*/, remove: [','], area: 'strHalfBottom' },
			]
		},

		// third
		{ if: new RegExp(rgxMid), area: 'thirdMidFull', 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strThird'},
				{ if: new RegExp(rgxRh), area: 'rhThirdBottom'}
			]
		},

		// cuos/chords
		{ if: new RegExp(rgxChords), area: 'cuo', 
			for: new RegExp("[^" + rgxChords + "]*", "i"),
			// for: /[^H|Y|I|O|TTT|TT|BL|B|L]*/i,
			do: [
				{ if: /[0-9]/, area: 'strHalf' },
				{ if: new RegExp("("+rgxLh + ")|(\\([0-9].*\\))"),
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'},
						{ if: new RegExp(rgxLh), area: 'thirdMidLeft' },
						{ if: /\(\d+\)/,
							for: /\(\d+\)/,
							do: [
								{ if: /\(\d.*\)/, remove: ['(', ')'], area: 'thirdMidRight' }
							]
						},
						{ if: /\(.*\..\)/, 
							for: /\(.*\..\)/,
							do: [
								{ if: /\(\d.*\./, remove: ['(', '.'], area: 'thirdMidRightTop' },
								{ if: /\.\d.*\)/, remove: [')', '.'], area: 'thirdMidRightBottom' }
							]
						},				
						{ if: /\(0\)/, 
							for: /.*/,
							do: [
								{ if: /0/, area: 'thirdMidFull'}
							]
						},
					]
				}
			]
		},
		{ if: new RegExp(rgxChords), area: 'cuo', 
			for: new RegExp("[" + rgxChords + "](.*)"),
			do: [
				{ if: /[0-9]/, area: 'strHalf' },
				{ if: new RegExp("("+rgxLh + ")|(\\([0-9].*\\))"),
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'},
						{ if: new RegExp(rgxLh), area: 'thirdMidLeft' },
						{ if: /\(\d+\)/,
							for: /\(\d+\)/,
							do: [
								{ if: /\(\d.*\)/, remove: ['(', ')'], area: 'thirdMidRight' }
							]
						},
						{ if: /\(.*\..\)/, 
							for: /\(.*\..\)/,
							do: [
								{ if: /\(\d.*\./, remove: ['(', '.'], area: 'thirdMidRightTop' },
								{ if: /\.\d.*\)/, remove: [')', '.'], area: 'thirdMidRightBottom' }
							]
						},				
						{ if: /\(0\)/, 
							for: /.*/,
							do: [
								{ if: /0/, area: 'thirdMidFull'}
							]
						},
					]
				}
			]
		},

		// overwrite
		{ if: /打圆|打圓/, area: 'chineseChar' }
	]
}