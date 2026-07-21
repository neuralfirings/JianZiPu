# python3 src/v3/fontForgeRun.py
# run this script to remove all characters from the font except the ones needed for input in the areaKeySVGMap.csv
# also add essential control characters and whitespace a-z, A-Z, 0-9
# 1. run this script in the fontforge terminal (script might take a while to run)
# 2. Encoding > Reencode > Glyph Order
# 3. Save As font as base font for use before importing any unicode


import os
import csv
from posix import truncate
import fontforge

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

def get_input_chars():
    """
    Extract unique individual characters from areaKeySVGMap.csv
    from columns: keys, latin, latin_alt, simplified, traditional
    """
    csv_path = HOME_PATH + '/input/areaKeySVGMap.csv'
    unique_chars = set()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Process each column that contains characters
                columns_to_process = ['common','latin', 'latin_alt', 'simplified', 'traditional']
                
                for column in columns_to_process:
                    if column in row and row[column]:
                        value = row[column].strip()
                        if value:  # Skip empty values
                            # Split by semicolon if multiple values
                            values = value.split(';')
                            for val in values:
                                val = val.strip()
                                if val:  # Skip empty values after splitting
                                    # Extract individual characters
                                    for char in val:
                                        if char.strip():  # Skip whitespace
                                            unique_chars.add(char)
        
        # Convert set to sorted list
        result = sorted(list(unique_chars))
        fontforge.logWarning(f"Extracted {len(result)} unique characters: {result}")
        return result
        
    except FileNotFoundError:
        fontforge.logWarning(f"CSV file not found: {csv_path}")
        return []
    except Exception as e:
        fontforge.logWarning(f"Error reading CSV file: {e}")
        return []

def remove_chars_except(chars_to_keep):
    """
    Remove all characters from the font except the specified characters.
    """
    # Get the currently active font
    current_font = fontforge.activeFont()
    
    if current_font is None:
        fontforge.logWarning("No active font found. Please open a font first.")
        return
    
    fontforge.logWarning(f"Processing font: {current_font.familyname}")
    fontforge.logWarning(f"Font path: {current_font.path}")
    
    # Get all glyph names in the font - iterate through the glyphs directly
    all_glyph_names = []
    for glyph in current_font.glyphs():
        all_glyph_names.append(glyph.glyphname)
    
    fontforge.logWarning(f"Total glyphs in font: {len(all_glyph_names)}")
    
    # Count glyphs to be removed
    glyphs_to_remove = []
    
    for glyph_name in all_glyph_names:
        # Skip if it's a special glyph (like .notdef, .null, etc.)
        if glyph_name.startswith('.'):
            continue

        # skip if unicode before or equal to U+00A0 (essentials + 00A0 = nbsp;)
        if current_font[glyph_name].unicode <= 0x00A0:
            continue
        
        # Check if this glyph represents one of our target characters
        should_keep = False
        for char in chars_to_keep:
            # Try to get the unicode value for the character
            try:
                char_unicode = ord(char)
                # Check if this glyph has the same unicode value
                if current_font[glyph_name].unicode == char_unicode:
                    should_keep = truncate
                    break
            except:
                # If we can't get unicode, check if the glyph name matches
                if glyph_name.lower() == char.lower():
                    should_keep = True
                    break
        
        if not should_keep:
            glyphs_to_remove.append(glyph_name)
    
    fontforge.logWarning(f"Glyphs to remove: {len(glyphs_to_remove)}")
    fontforge.logWarning(f"Glyphs to keep: {len(all_glyph_names) - len(glyphs_to_remove)}")
    
    # Remove the unwanted glyphs
    for glyph_name in glyphs_to_remove:
        try:
            current_font.removeGlyph(glyph_name)
            # fontforge.logWarning(f"Removed glyph: {glyph_name}")
        except Exception as e:
            fontforge.logWarning(f"Error removing glyph {glyph_name}: {e}")

    fontforge.logWarning("Character removal complete!")
# Essential control characters and whitespace
essential_chars = [
    '【', '】', '。', # might not need these
    '，',
    '：',
    '｜',
    '徽', '点', '點', '弦', '絃'
]

input_chars = get_input_chars()
input_chars.extend(essential_chars)
# unique chars
input_chars = list(set(input_chars))

fontforge.logWarning(f"Input chars (including essential): {input_chars}")
remove_chars_except(input_chars)

# add blanks
blank_glyph = current_font.createChar(0x58001)
blank_glyph.width = 0
blank_glyph.glyphname = "blank"

blank_glyph = current_font.createChar(0x58002)
blank_glyph.width = 500
blank_glyph.glyphname = "blank_bar"

blank_glyph = current_font.createChar(0x58003)
blank_glyph.width = 0
blank_glyph.glyphname = "blank_colon"

blank_glyph = current_font.createChar(0x58004)
blank_glyph.width = 1000
blank_glyph.glyphname = "advance"

blank_glyph = current_font.createChar(0x58005)
blank_glyph.width = 500
blank_glyph.glyphname = "half_advance"

