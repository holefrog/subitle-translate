#!/bin/bash

# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No color

# Trap any errors and display a message
trap 'echo -e "${RED}An error occurred. Exiting...${NC}"; exit 1;' ERR

# 在循环前检查文件
shopt -s nullglob
files=(*.ass)
if [ ${#files[@]} -eq 0 ]; then
    echo -e "${YELLOW}No .ass files found${NC}"
    exit 0
fi


# Loop through all .ass files in the current directory
for file in *.ass; do
    if [[ -f "$file" ]]; then
        filename="${file%.*}"  # Remove file extension
        # Convert .ass to .srt using ffmpeg
        ffmpeg -i "$file" "${filename}.srt"
        
        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}Conversion successful: $file -> ${filename}.srt${NC}"
        else
            echo -e "${RED}Failed to convert: $file${NC}"
        fi
    else
        echo -e "${YELLOW}No .ass files found in the current directory${NC}"
    fi
done

