#!/usr/bin/env bash

# Define a function to replace cubemaster with cubebox in a file
replace_cubemaster_with_cubebox() {
        tmpfile=$(mktemp)
        sed 's/cubemaster/cubebox/g' "$1" > "$tmpfile"
        sed 's/CubeMaster/CubeBox/g' "$tmpfile" > "$2"
        rm "$tmpfile"
}

# List of files to process
files=(
    "thecubeivazio.cubemaster.service"
    "launch_cubemaster.sh"
    "start_cubemaster_service.sh"
    "setup_cubemaster_service.sh"
    "check_cubemaster_status.sh"
    "update_and_launch_cubemaster.sh"
    "stop_cubemaster_service.sh"
    "view_cubemaster_logs.sh"
)

# Loop through the files and create new files with the replacements
for file in "${files[@]}"; do
    new_file=$(echo "$file" | sed 's/cubemaster/cubebox/g')
    replace_cubemaster_with_cubebox "$file" "$new_file"
done
