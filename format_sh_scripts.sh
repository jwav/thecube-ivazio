#!/bin/bash

# Check if shfmt is installed
if ! command -v shfmt &>/dev/null; then
  echo "shfmt could not be found. Please install shfmt first."
  exit 1
fi

# Find all .sh files and format them
shfmt -i 2 -w *.sh

# Output completion message
echo "SH scripts formatted."
