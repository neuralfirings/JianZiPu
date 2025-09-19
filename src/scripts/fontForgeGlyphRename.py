#!/usr/bin/env python3
"""
FontForge Python script to rename glyphs based on fontforgeGlyphRename.csv
If new_glyph_name column has a value, rename glyph to this value
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

def rename_glyphs_from_csv(csv_filename="fontforgeGlyphRename.csv"):
    """
    Rename glyphs based on the CSV file.
    If new_glyph_name column has a value, rename glyph to this value.
    """
    csv_path = os.path.join(HOME_PATH, 'input', csv_filename)
    
    if not os.path.exists(csv_path):
        fontforge.logWarning(f"CSV file not found: {csv_path}")
        return
    
    fontforge.logWarning(f"Processing font: {current_font.familyname}")
    fontforge.logWarning(f"Reading rename instructions from: {csv_path}")
    
    # Track statistics
    total_rows = 0
    renamed_count = 0
    skipped_count = 0
    error_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                total_rows += 1
                
                glyph_name = row.get('glyph_name', '').strip()
                new_glyph_name = row.get('new_glyph_name', '').strip()
                
                # Skip if no new name specified
                if not new_glyph_name:
                    skipped_count += 1
                    continue
                
                # Check if the glyph exists in the font
                if glyph_name not in current_font:
                    fontforge.logWarning(f"Glyph '{glyph_name}' not found in font, skipping...")
                    skipped_count += 1
                    continue
                
                # Check if the new name already exists
                if new_glyph_name in current_font:
                    fontforge.logWarning(f"Warning: New name '{new_glyph_name}' already exists, skipping rename of '{glyph_name}'")
                    skipped_count += 1
                    continue
                
                try:
                    # Get the glyph and rename it
                    glyph = current_font[glyph_name]
                    old_name = glyph.glyphname
                    
                    # Rename the glyph
                    glyph.glyphname = new_glyph_name
                    
                    fontforge.logWarning(f"Renamed: '{old_name}' -> '{new_glyph_name}'")
                    renamed_count += 1
                    
                except Exception as e:
                    fontforge.logWarning(f"Error renaming '{glyph_name}' to '{new_glyph_name}': {e}")
                    error_count += 1
                    continue
        
        # Summary
        fontforge.logWarning(f"\n=== Rename Summary ===")
        fontforge.logWarning(f"Total rows processed: {total_rows}")
        fontforge.logWarning(f"Successfully renamed: {renamed_count}")
        fontforge.logWarning(f"Skipped (no new name): {skipped_count}")
        fontforge.logWarning(f"Errors: {error_count}")
        fontforge.logWarning(f"=====================")
        
    except FileNotFoundError:
        fontforge.logWarning(f"CSV file not found: {csv_path}")
    except Exception as e:
        fontforge.logWarning(f"Error reading CSV file: {e}")

rename_glyphs_from_csv()