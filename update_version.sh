#!/usr/bin/env bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color


# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"

# Run the script logic inside a subshell
(
  cd "$SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

# TODO: by default, skip the APT update and pip install
SKIP_APT=true
SKIP_PIP_REQ=true

for arg in "$@"
do
  if [ "$arg" == "--full-update" ]; then
    SKIP_APT=false
    SKIP_PIP_REQ=false
    echo "Full update"
    break
  elif [ "$arg" == "--skip-apt" ]; then
    SKIP_APT=true
    echo "Skipping APT update and install"
  elif [ "$arg" == "--skip-pip" ]; then
    SKIP_PIP_REQ=true
    echo "Skipping pip install"
  fi
done


echo "Stashing local changes..."
git stash
echo "Pulling git..."
git pull
if [ $? -ne 0 ]; then
  echo -e "${RED}ERROR: git pull failed${NC}"
  exit 1
else
  echo -e "${GREEN}OK : git pull succeeded${NC}"
fi


if [ "$SKIP_APT" = false ]; then
  echo "Updating APT and installing required packages.."
  ./install_required_apt_packages.sh
  if [ $? -ne 0 ]; then
      echo -e "${RED}ERROR: APT udpate and install failed${NC}"
      exit 1
  else
    echo -e "${GREEN}OK : The script succeeded${NC}"
  fi
fi


if [ "$SKIP_PIP_REQ" = false ]; then
echo "pip install requirements..."
pip install -r ./requirements.txt
if [ $? -ne 0 ]; then
  echo -e "${RED}ERROR: pip install requirements failed${NC}"
  exit 1
else
  echo -e "${GREEN}OK : pip install requirements succeeded${NC}"
fi
fi

echo "Installing the project package..."
pip install .
if [ $? -ne 0 ]; then
  echo -e "${RED}ERROR: project package install failed${NC}"
  exit 1
else
  echo -e "${GREEN}OK : project package install succeeded${NC}"
fi

echo "Copying scripts..."
# if the hostname is cubemaster, copy the cubemaster scripts, otherwise copy the cubebox scripts
if [[ "$HOSTNAME" == "cubemaster" ]]; then
  for file in *cubemaster*; do
    cp "$file" ~/
    chmod +x ~/"$file"
  done
elif [[ "$HOSTNAME" == *"cubebox"* ]]; then
  for file in *cubebox*; do
    cp "$file" ~/
    chmod +x ~/"$file"
  done
fi


echo -e "${GREEN}Update OK: APT packages installed, git pulled, project package pip installed.${NC}"

) # End of subshell
