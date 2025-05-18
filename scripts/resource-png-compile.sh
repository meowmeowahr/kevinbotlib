#!/bin/bash

# Define source and destination directories
SVG_DIR="resources/kevinbotlib/theme_icons"
PNG_DIR="$SVG_DIR"

# Check if source directory exists
if [ ! -d "$SVG_DIR" ]; then
    echo "Error: Source directory $SVG_DIR does not exist."
    exit 1
fi

# Check if ImageMagick is installed
if ! command -v convert >/dev/null 2>&1; then
    echo "Error: ImageMagick (convert) not found."
    echo "Please install ImageMagick to convert SVG files."
    exit 1
fi

echo "Using ImageMagick for SVG to PNG conversion"

# List of SVG files to convert
SVG_FILES=(
    "checkbox-checked-dark.svg"
    "checkbox-checked-light.svg"
    "checkbox-checked-hover-dark.svg"
    "checkbox-checked-hover-light.svg"
    "checkbox-checked-disabled-dark.svg"
    "checkbox-checked-disabled-light.svg"
    "checkbox-indeterminate-dark.svg"
    "checkbox-indeterminate-light.svg"
    "checkbox-indeterminate-hover-dark.svg"
    "checkbox-indeterminate-hover-light.svg"
    "checkbox-indeterminate-disabled-dark.svg"
    "checkbox-indeterminate-disabled-light.svg"
    "splitter-grip-horizontal-dark.svg"
    "splitter-grip-horizontal-light.svg"
    "splitter-grip-vertical-dark.svg"
    "splitter-grip-vertical-light.svg"
)

# Base width (in pixels) at 1x - adjust as needed
BASE_WIDTH=24

# Base DPI (typically 96 for 1x)
BASE_DPI=96

# Convert SVG files to PNG at multiple resolutions
for svg_file in "${SVG_FILES[@]}"; do
    svg_path="$SVG_DIR/$svg_file"
    base_name="${svg_file%.svg}"
    
    if [ ! -f "$svg_path" ]; then
        echo "Warning: $svg_path does not exist. Skipping."
        continue
    fi
    
    # Array of resolutions to generate with corresponding DPI and suffixes
    declare -A RESOLUTIONS=(
        [""]="$BASE_DPI $BASE_WIDTH"                  # Base resolution (1x)
        ["-2x"]="$((BASE_DPI * 2)) $((BASE_WIDTH * 2))"  # 2x resolution
        ["-4x"]="$((BASE_DPI * 4)) $((BASE_WIDTH * 4))"  # 4x resolution
    )
    
    for suffix in "" "-2x" "-4x"; do
        # Split the resolution string into DPI and width
        read dpi width <<< "${RESOLUTIONS[$suffix]}"
        png_path="$PNG_DIR/${base_name}${suffix}.png"
        
        echo "Converting $svg_path to $png_path (${width}px) using ImageMagick..."
        convert -background none -density "$dpi" -units PixelsPerInch "$svg_path" -resize "${width}x${width}" "$png_path"
        
        if [ $? -eq 0 ]; then
            echo "Successfully converted $svg_file to ${base_name}${suffix}.png"
        else
            echo "Error converting $svg_file to ${base_name}${suffix}.png"
        fi
    done
done

echo "Conversion complete! All PNGs (-1x, -2x, -4x) saved to $PNG_DIR"