#!/bin/bash

# Check if correct arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <file_list.txt> <output_file>"
    exit 1
fi

# Read arguments
file_list="$1"
output_file="$2"

# Clear the output file if it exists
> "$output_file"

# Read file list into an array, ignoring lines that start with '#'
mapfile -t files < <(grep -v '^#' "$file_list")

# Process each file entry
for file in "${files[@]}"; do
    file=$(echo "$file" | xargs)  # Trim spaces
    
    # Expand wildcards and concatenate files
    for expanded_file in $file; do
        if [[ -f "$expanded_file" ]]; then
            cat "$expanded_file" >> "$output_file"
            echo "" >> "$output_file"  # Always add a newline after each file
        else
            echo "Warning: '$expanded_file' does not exist or is not a valid file."
        fi
    done
done

echo "Concatenation complete. Output file: $output_file"
