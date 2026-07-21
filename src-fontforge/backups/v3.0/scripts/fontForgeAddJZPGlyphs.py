#!/usr/bin/env python3
"""
FontForge Python script to import all SVG files from ./components/ folder
and create glyphs with PUA (Private Use Area) unicode values.
"""

import fontforge
import os
import csv
import glob
import xml.etree.ElementTree as ET

# Get the current font, set HOME_PATH and FILE_NAME
current_font = fontforge.activeFont()
if current_font is not None:
    file_path = current_font.path
    if file_path is not None:
        HOME_PATH = os.path.dirname(file_path)
        FILE_NAME = os.path.basename(file_path)
    else:
        fontforge.logWarning("No file is currently open.")
else:
    fontforge.logWarning("No active font found.")

def get_svg_bounds(svg_file):
    """Get the bounding box of an SVG file before importing."""
    try:
        tree = ET.parse(svg_file)
        root = tree.getroot()
        
        # Check for viewBox attribute first
        viewbox = root.get('viewBox')
        if viewbox:
            # viewBox format: "x y width height"
            parts = viewbox.split()
            if len(parts) == 4:
                x, y, width, height = map(float, parts)
                return (x, y, x + width, y + height)
        
        # Fallback to width/height attributes
        width = root.get('width')
        height = root.get('height')
        if width and height:
            # Remove units if present (e.g., "100px" -> 100)
            w = float(width.replace('px', '').replace('pt', ''))
            h = float(height.replace('px', '').replace('pt', ''))
            return (0, 0, w, h)
            
    except Exception as e:
        fontforge.logWarning(f"Error parsing SVG bounds: {e}")
    
    return None

def add_pua_glyphs(start_unicode=58101):
    """
    Import all SVG files from ./components/ folder and create glyphs.
    
    Args:
        start_unicode (int): Starting unicode value for PUA (default: 58001)
        export_csv_name (str): Name of the CSV file to export (default: "componentUnicodeMap.csv")
    """
    # Get the currently active font
    current_font = fontforge.activeFont()
    
    if current_font is None:
        fontforge.logWarning("No active font found. Please open a font first.")
        return
    
    fontforge.logWarning(f"Processing font: {current_font.familyname}")
    fontforge.logWarning(f"Font path: {current_font.path}")
    
    # Get the components directory path
    components_path = os.path.join(HOME_PATH, 'components')
    
    # Check if components directory exists
    if not os.path.exists(components_path):
        fontforge.logWarning(f"Components directory not found: {components_path}")
        return
    
    # Find all SVG files in the components directory
    svg_files = glob.glob(os.path.join(components_path, '*.svg'))
    
    if not svg_files:
        fontforge.logWarning(f"No SVG files found in: {components_path}")
        return
    
    fontforge.logWarning(f"Found {len(svg_files)} SVG files")
    
    # Data to export to CSV
    csv_data = []
    current_unicode = start_unicode
    
    # Process each SVG file
    for svg_file in sorted(svg_files):
        # Get the base filename without extension
        base_name = os.path.splitext(os.path.basename(svg_file))[0]
        
        # Skip if glyph already exists
        if base_name in current_font:
            fontforge.logWarning(f"Glyph '{base_name}' already exists, skipping...")
            continue

        # Get SVG bounds before processing
        svg_bounds = get_svg_bounds(svg_file)
        # fontforge.logWarning(f"SVG bounds for {base_name}: {svg_bounds}")
        
        try:
            # Create new glyph
            glyph = current_font.createChar(current_unicode, base_name)
            
            # Import SVG outlines
            glyph.importOutlines(svg_file, scale=False)
            
            # Set glyph width (you can adjust this as needed)
            glyph.width = 0

            # Move glyph to (0, 0) using SVG bounds if available
            if svg_bounds:
                # svg_bounds format: (0, 0, width, height)
                offset_x = 0 #-svg_bounds[2]  # not needed
                offset_y = -(820-svg_bounds[3])  # Move bottom edge to 0 
                glyph.transform((1, 0, 0, 1, offset_x, offset_y))
                # fontforge.logWarning(f"Positioned using SVG bounds: offset({offset_x}, {offset_y})")
            else:
                # Fallback to glyph bounding box
                bb = glyph.boundingBox()
                if bb:
                    offset_x = -bb[0]  # Move left edge to 0
                    offset_y = -bb[1]  # Move bottom edge to 0
                    glyph.transform((1, 0, 0, 1, offset_x, offset_y))
                    fontforge.logWarning(f"NO SVG BOUNDS! Positioned using glyph bounds: offset({offset_x}, {offset_y})")
            
            # Clean up the glyph
            glyph.removeOverlap()
            glyph.addExtrema()
            
            # Add to CSV data
            csv_data.append({
                'svg': os.path.basename(svg_file),
                'glyph_name': base_name,
                'unicode': current_unicode
            })
            
            # fontforge.logWarning(f"Created glyph '{base_name}' with unicode {current_unicode}")
            
            # Increment unicode for next glyph
            current_unicode += 1
            
        except Exception as e:
            fontforge.logWarning(f"Error processing {svg_file}: {e}")
            continue

add_pua_glyphs()