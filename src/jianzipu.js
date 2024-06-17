DEBUG = false

////////////////////////////////////////////////////////////////////////

function getStructure(ogStr, structureMap) {
	var strMap = {}
	var str = ogStr.match(structureMap.for)[0]
	var startIdx = ogStr.match(structureMap.for).index
	for (var i=0; i<structureMap.do.length; i++) {
		if (str.match(structureMap.do[i].if)) {
			var matchInfo = str.match(structureMap.do[i].if)
			if (matchInfo.index != undefined) {
				if (structureMap.do[i].area != undefined) {
					var matchChar = structureMap.do[i].use != undefined ? structureMap.do[i].use : matchInfo[0]
					if (structureMap.do[i].remove != undefined) {
						for (var j=0; j<structureMap.do[i].remove.length; j++) {
							matchChar = matchChar.replaceAll(structureMap.do[i].remove[j], '')
						}
					}
					strMap[matchInfo.index + startIdx] = {
						chars: matchChar,
						length: matchInfo[0].length, 
						area: structureMap.do[i].area
					}
					for (var j=1;j<matchInfo[0].length;j++) {
						delete strMap[matchInfo.index + startIdx + j] 
					}
				}
				if (structureMap.do[i].for != undefined) {
					subStrMap = getStructure(str, structureMap.do[i])
					for (var k in subStrMap) {
						strMap[Number(k) + startIdx] = subStrMap[k]
						for (var j=1;j<subStrMap[k].length;j++) {
							delete strMap[Number(k) + startIdx + j]
						}
					}
					DEBUG ? console.log('subStrMap', subStrMap) : 0
				}
			}
			else if (false) { // for multimatches (e.g., with /g tag); ignoring for now tho
				var j=0
				while (j<100 && (matchPartInfo = structureMap.do[i].if.exec(str)) != null) {
					strMap[matchInfo.index] = {
						chars: matchInfo[0],
						length: matchPartInfo[0].length, 
						areas: structureMap.do[i].areas
					}
					strMapAreas = strMapAreas.concat(structureMap.do[i].areas)
				  j++
				}
			}
		}
	}
	return strMap
}

function jianZiToStr(str) {
	alphaNumArr = str.trim().split(/(\d+(?:\.\d+)?)/);
	DEBUG ? console.log('alphaNumArr', alphaNumArr) : ""
	countNumbers = alphaNumArr.filter(e => !isNaN(e) && e != "").length
	if (countNumbers > 1 || (countNumbers == 1 && str.indexOf("掐起") > -1)) {
		firstNumIdx = alphaNumArr.findIndex(e => !isNaN(e) && e != "")
		firstNumStr = alphaNumArr[firstNumIdx]
		// the next section converts 34 to 3.4, 12 to 12, 1.2 to 1.2, 125 to 12.5
		if (firstNumStr.indexOf(".") == -1) {
			if (["10", "11", "12", "13"].indexOf(firstNumStr.substring(0,2)) > -1) {
				if (firstNumStr.length >= 3) {
					firstNumStr = firstNumStr.slice(0, -1) + "." + firstNumStr.slice(-1);
				}
			}
			else {
				if (firstNumStr.length >= 2) {
					firstNumStr = firstNumStr.slice(0, -1) + "." + firstNumStr.slice(-1);
				}
			}
		}
		alphaNumArr[firstNumIdx] = ''
		UIndx = alphaNumArr.findIndex(e => e === "U" || e === "历" || e === "歷")
		if (UIndx > -1) {
			DEBUG ? console.log('UIndx', alphaNumArr) : ""
			if (alphaNumArr[UIndx+1] != undefined && !alphaNumArr[UIndx+1].isNaN) {
				commaMe = alphaNumArr[UIndx+1]
				alphaNumArr[UIndx+1] = commaMe.slice(0, -1) + "," + commaMe.slice(-1);
			}
		}
		alphaNumArr.push(`(${firstNumStr})`)
	}
	str = alphaNumArr.join('')
	DEBUG ? console.log('new str', str) : ""
	return str
}

function cuoJianZiToStr(str) {
	lastChar = str.slice(-1)
	if (Number(lastChar) >= 1 && Number(lastChar) <= 7) {
		stringNum = lastChar
		str = str.slice(0, -1) + "l" + stringNum // hack: insert a "l" here to break up the hui and string numbers, will remove a few lines down
		str = jianZiToStr(str)
		str = str.replace('l', '') // whoop there it is
	}
	return str
}

function stringToCharacter(str) {
	// str = str.replaceAll('V', 'Vv')
	str = str.replaceAll('（', '(')
		.replaceAll('）', ')')
		.replaceAll('。', '.')
		.replaceAll('散', '0')
		.replaceAll('四', '4')
		.replaceAll('五', '5')
		.replaceAll('六', '6')
		.replaceAll('七', '7')
		.replaceAll('八', '8')
		.replaceAll('九', '9')
		.replaceAll('一一', '1.1')
		.replaceAll('一二', '1.2')
		.replaceAll('一三', '1.3')
		.replaceAll('十一', '11')
		.replaceAll('十二', '12')
		.replaceAll('十三外', '13.5')
		.replaceAll('外', '13.5')
		.replaceAll('十三', '13')
		.replaceAll('一', '1')
		.replaceAll('二', '2')
		.replaceAll('三', '3')
		.replaceAll('十', '10')
		.replaceAll('半轮', 'banlun')
		.replaceAll('半', '.5') 
	
	// following are new
	if (str.indexOf('(') == -1) {
		// cuo
		const cuoStarters = [
			"Y", "FC", "反撮", "反撮",
			"I", "DC", "大撮", "大撮",
			"O", "DFC", "大反撮", "大反撮", 
			"H", "C", "撮", "撮",
		];
		if (cuoStarters.some(substring => str.startsWith(substring))) {
			const cuoType = cuoStarters.filter(substring => str.startsWith(substring))[0];
			DEBUG ? console.log('cuoType', cuoType) : ''	
			str = str.replace(cuoType, '');
			strParts = str.split('|');
			DEBUG ? console.log('strParts', strParts) : ''
			strParts[0] = cuoJianZiToStr(strParts[0]);
			strParts[1] = cuoJianZiToStr(strParts[1]);
			str = strParts[0] + cuoType + strParts[1];
		}
		// no cuo
		else {
			str = jianZiToStr(str)
		}
	}
	if (str.length != 1) { str = str.replaceAll('急', '>') }
	// end new

	var strMap = getStructure(str, charRules)
	DEBUG ? console.log('strMap', strMap) : ''

	// get unicodes
	var character = '';
	for (var k in strMap) {
		for (var i=0;i<charMap[strMap[k].area].components.length; i++) {
			if (charMap[strMap[k].area].components[i].keys.some(v => v === strMap[k].chars)) {
				character += String.fromCharCode(charMap[strMap[k].area].components[i].unicode)
			}
		}
	}
	return character
}
function paragraphToCharacters(para) {
	var lines = para.split('\n')
	for (var j=0;j<lines.length; j++) {
		var words = lines[j].split(' ')
		for (var i=0;i<words.length;i++) {
			var cuo1, cuo2, translation
			if (false && words[i].split('H').length > 1) {
				cuo1 = words[i].split('H')[0]
				cuo2 = words[i].split('H')[1]
				translation = stringToCharacter(cuo1) + stringToCharacter('H') + stringToCharacter(cuo2)
			}
			else {
				translation = stringToCharacter(words[i])
			}
			words[i] = translation == '' && words[i] != '' ? words[i] : translation + ' '
		}
		lines[j] = words.join('')
	}
	return lines.join('\n')
}

////////////////////////////////////////////////////////////////////////

document.addEventListener("DOMContentLoaded", function(event) { 
	var jzpInBrackets = document.getElementsByClassName("jzp")
	for (var i=0;i<jzpInBrackets.length;i++) {
		let newDivHTML = jzpInBrackets[i].innerHTML
		newDivHTML = newDivHTML.replaceAll('[[[', '<span class="jzp-font jzp-characters">').replaceAll(']]]', '</span>')
		newDivHTML = newDivHTML.replaceAll('[[', '<span class="jzp-font">').replaceAll(']]', '</span>')
		jzpInBrackets[i].innerHTML = newDivHTML
		jzpInCharacters = jzpInBrackets[i].getElementsByClassName("jzp-characters")
		for (var j=0;j<jzpInCharacters.length;j++) {
			jzpInCharacters[j].innerText = paragraphToCharacters(jzpInCharacters[j].innerText)
		}
	}
})
