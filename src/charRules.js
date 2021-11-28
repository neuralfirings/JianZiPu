const charRules = {
	for: /.*/,
	do: [
		{ if: /[0-9]/, area: 'strFull'},
		{ if: /(n|k|l|h|u|i|o|c|U)/, area: 'rhFull'},
		{ if: /\(\d.*\)/, 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: /(n|k|l|h|u|i|o|c|U)/, area: 'rhHalf'},
			]
		},
		{ if: /(s|d|v|f|x)/, area: 'lhHalf',
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strHalf'},
				{ if: /(n|k|l|h|u|i|o|c|U)/, area: 'rhHalf'},
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
		{ if: /j|V/, area: 'thirdMidFull', 
			for: /.*/,
			do: [
				{ if: /[0-9]/, area: 'strThird'},
				{ if: /(n|k|l|h|u|i|o|c)/, area: 'rhThirdBottom'}
			]
		},
		{ if: /\(0\)/, 
			for: /\(0\)/,
			do: [
				{ if: /0/, area: 'huiHalfFull'}
			]
		},
		{ if: /\//, area: 'halfUpper' },
		{ if: /\\/, area: 'halfLeft'  },
		{ if: /H|Y|I|O/, area: 'cuo', 
			for: /[^H|Y|I|O]*/i,
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
		{ if: /H|Y|I|O/, area: 'cuo', 
			for: /[H|Y|I|O](.*)/,
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
	]
}