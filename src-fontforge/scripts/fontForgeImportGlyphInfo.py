"""
FontForge Python script to import glyph information from fontforgeGlyphInfo.csv
Creates glyphs with specified unicode values and glyph names.
"""

import fontforge
import os
import csv

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

def import_glyph_info(csv_filename="fontforgeGlyphInfo.csv"):
    """
    Import glyph information from CSV file and create/update glyphs
    """
    csv_path = os.path.join(HOME_PATH, 'output', csv_filename)
    
    if not os.path.exists(csv_path):
        fontforge.logWarning(f"CSV file not found: {csv_path}")
        return
    
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            imported_count = 0
            skipped_count = 0
            
            for row in reader:
                try:
                    unicode_value = int(row['unicode_value'])
                    glyph_name = row['glyph_name'].strip()
                    
                    # Skip empty glyph names
                    if not glyph_name:
                        continue
                    
                    # Check if glyph already exists
                    if glyph_name in current_font:
                        existing_glyph = current_font[glyph_name]
                        # Update unicode if different
                        if unicode_value != -1 and existing_glyph.unicode != unicode_value:
                            existing_glyph.unicode = unicode_value
                            fontforge.logWarning(f"Updated unicode for existing glyph: {glyph_name} -> U+{unicode_value:04X}")
                        else:
                            fontforge.logWarning(f"Glyph already exists: {glyph_name}")
                        skipped_count += 1
                        continue
                    
                    # Create new glyph
                    if unicode_value != -1:
                        # Create glyph with unicode value
                        new_glyph = current_font.createChar(unicode_value, glyph_name)
                        fontforge.logWarning(f"Created glyph: {glyph_name} (U+{unicode_value:04X})")
                    else:
                        # Create glyph without unicode (like .notdef, .null, etc.)
                        new_glyph = current_font.createChar(-1, glyph_name)
                        fontforge.logWarning(f"Created glyph without unicode: {glyph_name}")
                    
                    imported_count += 1
                    
                except ValueError as e:
                    fontforge.logWarning(f"Error processing row {row}: {e}")
                    continue
                except Exception as e:
                    fontforge.logWarning(f"Error creating glyph {glyph_name}: {e}")
                    continue
        
        fontforge.logWarning(f"Import completed: {imported_count} glyphs created, {skipped_count} glyphs skipped")
        
    except Exception as e:
        fontforge.logWarning(f"Error reading CSV file: {e}")

def main():
    """Main function to run the import"""
    fontforge.logWarning("Starting glyph import from fontforgeGlyphInfo.csv...")
    import_glyph_info()
    fontforge.logWarning("Glyph import completed.")

if __name__ == "__main__":
    main()

import_glyph_info()