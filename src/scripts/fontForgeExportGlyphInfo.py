#!/usr/bin/env python3
"""
FontForge Python script to export current glyph names
"""

import os
import csv
import fontforge

# Get the current font, set HOME_PATH and FILE_NAME
current_font = fontforge.activeFont()
if current_font is None:
    fontforge.logWarning("No active font found. Please open a font first.")
    exit()

file_path = current_font.path
if file_path is not None:
    HOME_PATH = os.path.dirname(file_path)
    FILE_NAME = os.path.basename(file_path)
else:
    fontforge.logWarning("No file is currently open.")
    exit()

def export_current_glyph_names(filename="fontforgeGlyphInfo.csv"):
    """
    Export current glyph names for verification
    """
    csv_path = os.path.join(HOME_PATH, 'output', filename)
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['unicode_value', 'glyph_name', 'unicode_char']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for glyph in current_font.glyphs():
                glyph_name = glyph.glyphname
                unicode_value = glyph.unicode if hasattr(glyph, 'unicode') else -1
                
                if unicode_value != -1:
                    try:
                        unicode_char = chr(unicode_value)
                    except (ValueError, OverflowError):
                        unicode_char = ""
                else:
                    unicode_char = ""
                
                writer.writerow({
                    'glyph_name': glyph_name,
                    'unicode_value': unicode_value,
                    'unicode_char': unicode_char
                })
        
        fontforge.logWarning(f"Current glyph names exported to: {csv_path}")
        
    except Exception as e:
        fontforge.logWarning(f"Error exporting current glyph names: {e}")

export_current_glyph_names()