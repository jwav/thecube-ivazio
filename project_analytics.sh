#!/bin/bash

# Hardcoded list of directories to exclude
excluded_dirs=(
    "./build"
    "./thecubeivazio.egg-info"
    "./venv"
    "./venv_windows"
    "./thecubeivazio/__pycache__"
)

excluded_filenames=(
    "resources_rc.py"
)

# Construct the find command with directory exclusions
find_cmd='find . -name "*.py" -type f'
for dir in "${excluded_dirs[@]}"; do
    find_cmd+=" -not -path \"$dir\" -not -path \"$dir/*\""
done

# Execute the find command and filter out the excluded filenames
handled_files=$(eval "$find_cmd" | sort | uniq | grep -v -F -f <(printf "%s\n" "${excluded_filenames[@]}"))

# Initialize counters
total_lines=0
file_count=0

# Loop through each file and count lines
while IFS= read -r file; do
    if [[ -f "$file" ]]; then
        lines=$(wc -l < "$file")
        echo "$lines : $file"
        total_lines=$((total_lines + lines))
        file_count=$((file_count + 1))
    fi
done <<< "$handled_files"

# Output totals
echo "Total Python files: $file_count"
echo "Total lines of code: $total_lines"
