const charRules = {
	for: /.*/,
	do: [
		{ if: /[0-9]/, area: 'strFull'},
		{ if: /(n|ki|k|lo|l|h|u|i|o|c|U)/, area: 'rhFull'},
		{ if: /\(\d.*\)/, 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: /(n|ki|k|lo|h|u|i|o|c|U)/, area: 'rhHalf'},
			]
		},
		{ if: /(s|d|v|f|x)/, area: 'lhHalf',
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: /(n|ki|k|lo|l|h|u|i|o|c|U)/, area: 'rhHalf'},
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
		{ if: /[0-9],[0-9]/, 
			for: /[0-9],[0-9]/,
			do: [
				{ if: /\d.*\,/, remove: [','], area: 'strHalfTop' },
				{ if: /\,\d.*/, remove: [','], area: 'strHalfBottom' },
			]
		},
		{ if: /j|V|GF|G|F|D/, area: 'thirdMidFull', 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strThird'},
				{ if: /(n|ki|k|lo|l|h|u|i|o|c)/, area: 'rhThirdBottom'}
			]
		},
		{ if: /\(0\)/, 
			for: /\(0\)/,
			do: [
				{ if: /0/, area: 'huiHalfFull'}
			]
		},
		{ if: /\/|\>/, area: 'halfUpper' },
		{ if: /\\/, area: 'halfLeft'  },
		{ if: /H|Y|I|O|TTT|TT|BL|B|L/, area: 'cuo', 
			for: /[^H|Y|I|O|TTT|TT|BL|B|L]*/i,
			do: [
				{ if: /[0-9]/, area: 'strHalf' },
				{ if: /(s|d|v|f|x)|(\([0-9].*\))/,
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'},
						{ if: /s|d|v|f|x/, area: 'thirdMidLeft' },
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
		{ if: /H|Y|I|O|TTT|TT|BL|B|L/, area: 'cuo', 
			for: /[H|Y|I|O|TTT|TT|BL|B|L](.*)/,
			do: [
				{ if: /[0-9]/, area: 'strHalf' },
				{ if: /(s|d|v|f|x)|(\([0-9].*\))/,
					for: /.*/,
					do: [
						{ if: /[0-9]/, area: 'strThird'},
						{ if: /s|d|v|f|x/, area: 'thirdMidLeft' },
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
		{ if: /退/, area: 'chineseChar' },
		{ if: /长吟|長吟/, use: '长吟', area: 'chineseChar' },
		{ if: /细吟/, area: 'chineseChar' },
		{ if: /进|進/, use: '进', area: 'chineseChar' },
		{ if: /分开/, area: 'chineseChar' },
		{ if: /泛止/, area: 'chineseChar' },
		{ if: /大息/, area: 'chineseChar' },
		{ if: /少息/, area: 'chineseChar' },
		{ if: /复/, area: 'chineseChar' },
		{ if: /起/, area: 'chineseChar' },
		{ if: /泛起/, area: 'chineseChar' },
		{ if: /带起/, area: 'chineseChar' },
		{ if: /对起/, area: 'chineseChar' },
		{ if: /爪起/, area: 'chineseChar' },
		{ if: /撇起/, area: 'chineseChar' },
	]
}