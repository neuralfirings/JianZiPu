DEBUG = true

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
function stringToCharacter(str) {
	str = str.replaceAll('V', 'Vv')
	var strMap = getStructure(str, charRules)
	DEBUG ? console.log('strMap', strMap) : ''

	// get unicodes
	var character = '';
	for (var k in strMap) {
		for (var i=0;i<charMap[strMap[k].area].components.length; i++) {
			if (charMap[strMap[k].area].components[i].key == strMap[k].chars) {
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
