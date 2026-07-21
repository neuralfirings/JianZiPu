import os
import fontforge

def get_current_font():
    """Get the currently active font in FontForge."""
    current_font = fontforge.activeFont()
    if current_font is None:
        fontforge.logWarning("No active font found. Please open a font first.")
        return None
    return current_font

def get_font_path_info(current_font):
    """Get font path information."""
    file_path = current_font.path
    if file_path is None:
        fontforge.logWarning("No file is currently open.")
        return None, None
    
    home_path = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    return home_path, file_name

def validate_features_file(features_file_path):
    """Validate that the features file exists and is readable."""
    if not os.path.exists(features_file_path):
        fontforge.logWarning(f"Features file not found: {features_file_path}")
        return False
    
    if not os.path.isfile(features_file_path):
        fontforge.logWarning(f"Path is not a file: {features_file_path}")
        return False
    
    if not os.access(features_file_path, os.R_OK):
        fontforge.logWarning(f"Cannot read features file: {features_file_path}")
        return False
    
    return True

def replace_features(current_font, features_file_path):
    """
    Clears all existing features from a font and imports new ones from a .fea file.
    
    Args:
        current_font: The active FontForge font object
        features_file_path (str): The path to the new OpenType feature file ('.fea').
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate features file
        if not validate_features_file(features_file_path):
            return False
        
        # Clear existing lookups and features
        fontforge.logWarning("Clearing existing OpenType features...")
        
        # Get existing lookups using the correct FontForge API
        existing_lookups = []
        for lookup in current_font.gsub_lookups:
            existing_lookups.append(lookup)
        for lookup in current_font.gpos_lookups:
            existing_lookups.append(lookup)
        
        fontforge.logWarning(f"Found {len(existing_lookups)} existing lookups to remove...")
        
        # Remove lookups
        for lookup_name in existing_lookups:
            try:
                current_font.removeLookup(lookup_name)
                fontforge.logWarning(f"Removed lookup: {lookup_name}")
            except Exception as e:
                fontforge.logWarning(f"Failed to remove lookup '{lookup_name}': {e}")
        
        # Import new features from the .fea file
        fontforge.logWarning(f"Importing new features from {features_file_path}...")
        current_font.mergeFeature(features_file_path)
        
        # Verify the import was successful
        new_lookups = []
        for lookup in current_font.gsub_lookups:
            new_lookups.append(lookup)
        for lookup in current_font.gpos_lookups:
            new_lookups.append(lookup)
        
        fontforge.logWarning(f"Successfully imported features. New lookups: {len(new_lookups)}")
        
        if new_lookups:
            fontforge.logWarning("New lookups:")
            for lookup in new_lookups:
                fontforge.logWarning(f"  - {lookup}")
        
        fontforge.logWarning("Features replaced successfully.")
        return True
        
    except Exception as e:
        fontforge.logWarning(f"An error occurred while replacing features: {e}")
        return False

def main():
    """Main function to execute the feature refresh process."""
    fontforge.logWarning("===== starting =====")
    
    # Get current font
    current_font = get_current_font()
    if current_font is None:
        return False
    
    # Get font path information
    home_path, file_name = get_font_path_info(current_font)
    if home_path is None:
        return False
    
    # fontforge.logWarning(f"Working with font: {file_name}")
    # fontforge.logWarning(f"Font directory: {home_path}")
    
    # Define features file path
    features_filename = "fontForgeFeatures.fea"
    features_file_path = os.path.join(home_path, 'output', features_filename)
    
    # Replace features
    success = replace_features(current_font, features_file_path)
    
    if success:
        fontforge.logWarning("===== done =====")
    else:
        fontforge.logWarning("===== errored =====")
    
    return success

# Execute the main function
if __name__ == "__main__":
    main()

