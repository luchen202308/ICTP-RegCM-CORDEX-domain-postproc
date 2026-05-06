#!/bin/bash

# Script to replace ICT25_ESP with ICT26_ESP in files
# Usage: ./replace_string.sh [directory]
# Note: Only searches the specified directory, not subdirectories
# Note: Will not modify itself

# Get the script's own name
SCRIPT_NAME=$(basename "$0")

# Set the directory to search (default to current directory if not specified)
SEARCH_DIR="${1:-.}"

# Check if directory exists
if [ ! -d "$SEARCH_DIR" ]; then
    echo "Error: Directory '$SEARCH_DIR' does not exist"
    exit 1
fi

echo "Searching for files containing 'ICT25_ESP' in: $SEARCH_DIR (top-level only)"
echo "Excluding script itself: $SCRIPT_NAME"
echo "----------------------------------------"

# Find all files in the current directory only (not subdirectories) containing the string
# Exclude the script itself
find "$SEARCH_DIR" -maxdepth 1 -type f -not -name "$SCRIPT_NAME" -exec grep -l "ICT25_ESP" {} \; | while read -r file; do
    echo "Processing: $file"
    # Create a backup with .bak extension (optional - remove if not needed)
    #cp "$file" "$file.bak"
    # Replace the string in the file
    sed -i 's/ICT25_ESP/ICT26_ESP/g' "$file"
    echo "  ✓ Updated"
done

echo "----------------------------------------"
echo "Replacement complete!"
