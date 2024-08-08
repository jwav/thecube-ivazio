#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

DEBUG=true
SKIP_APT=false
SKIP_PIP_REQ=false
SKIP_GIT=false
SKIP_PROJECT_PACKAGE=false

generate_cubebox_scripts_from_cubemaster_scripts() {
  echo_red "Function deprecated."
  return 1
#  echo_blue "Generating cubeboxes scripts from the cubemaster scripts..."
#
#  # Define a function to replace cubemaster with cubebox in a file
#  replace_cubemaster_with_cubebox() {
#    local temp_file=$(mktemp)
#    sed 's/cubemaster/cubebox/g' "$1" >"$temp_file"
#    sed 's/CubeMaster/CubeBox/g' "$temp_file" >"$2"
#    rm "$temp_file"
#  }
#
#  # List of files to process
#  local files=(
#    "thecubeivazio.cubemaster.service"
#    "launch_cubemaster.sh"
#    "start_cubemaster_service.sh"
#    "setup_cubemaster_service.sh"
#    "check_cubemaster_status.sh"
#    "update_and_launch_cubemaster.sh"
#    "stop_cubemaster_service.sh"
#    "view_cubemaster_logs.sh"
#  )
#
#  # Loop through the files and create new files with the replacements
#  for file in "${files[@]}"; do
#    local new_file=$(echo "$file" | sed 's/cubemaster/cubebox/g')
#    replace_cubemaster_with_cubebox "$file" "$new_file"
#  done
}

copy_relevant_scripts_to_home() {
  # Initialize an array for scripts to copy
  local scripts_to_copy=(
    "activate_venv.sh"
    "install_required_apt_packages.sh"
    "*update*.sh"
    "*thecube*.sh"
    "configure_ssh_firewall.sh"
  )

  # Initialize an array for the filtered scripts
  local filtered_scripts=()

  # Function to add scripts based on pattern
  add_scripts() {
    local pattern=$1
    for file in $pattern; do
      if [[ -f "$file" ]]; then
        filtered_scripts+=("$file")
      fi
    done
  }

  # Function to exclude scripts based on pattern
#  exclude_scripts() {
#    local pattern=$1
#    local temp_array=()
#    for script in "${filtered_scripts[@]}"; do
#      if [[ "$script" != "$pattern" ]]; then
#        temp_array+=("$script")
#      fi
#    done
#    filtered_scripts=("${temp_array[@]}")
#  }

  # Add the general scripts
  for script in "${scripts_to_copy[@]}"; do
    add_scripts "$script"
  done

#  # Modify the list based on the hostname
#  if [[ "$CUBE_HOSTNAME" == "cubemaster" ]]; then
#    echo "Hostname is cubemaster. Adding cubemaster scripts and excluding cubebox scripts..."
#    add_scripts "*cubemaster*.sh"
#    exclude_scripts "*cubebox*.sh"
#  elif [[ "$CUBE_HOSTNAME" == *"cubebox"* ]]; then
#    echo "Hostname contains cubebox. Adding cubebox scripts and excluding cubemaster scripts..."
#    add_scripts "*cubebox*.sh"
#    exclude_scripts "*cubemaster*.sh"
#  fi

  # Copy and chmod+x the filtered scripts
  for script in "${filtered_scripts[@]}"; do
    echo_blue "Copying $script to home directory and making it executable."
    cp "$script" ~/
    chmod +x ~/"$script"
  done
}

setup_relevant_service() {
  setup_thecube_service
}

handle_arguments() {
  for arg in "$@"; do
    if [ "$arg" == "--full-update" ]; then
      SKIP_APT=false
      SKIP_PIP_REQ=false
      echo_blue "Full update"
      break
    elif [ "$arg" == "--skip-apt" ]; then
      SKIP_APT=true
      echo_blue "Skipping APT update and install"
    elif [ "$arg" == "--skip-pip" ]; then
      SKIP_PIP_REQ=true
      echo_blue "Skipping pip install"
    elif [ "$arg" == "--skip-git" ]; then
      SKIP_GIT=true
      echo_blue "Skipping git pull"
    elif [ "$arg" == "--skip-project-package" ]; then
      SKIP_PROJECT_PACKAGE=true
      echo_blue "Skipping project package install"
    # skip-all
    elif [ "$arg" == "--skip-all" ]; then
      SKIP_APT=true
      SKIP_PIP_REQ=true
      SKIP_GIT=true
      SKIP_PROJECT_PACKAGE=true
      echo_blue "Skipping all"
      # if debug
    elif [ "$arg" == "--debug" ]; then
      DEBUG=true
    fi

  done

      apply_debug

  echo_blue "Arguments handled."
}

apply_debug() {
  if [ "$DEBUG" = true ]; then
      echo_blue "Debug mode"
      SKIP_APT=true
      SKIP_PIP_REQ=true
      SKIP_GIT=false
      SKIP_PROJECT_PACKAGE=false
  fi
}

do_git_pull() {
  if [ "$SKIP_GIT" = false ]; then
    echo_blue "Stashing local changes..."
    git stash
    echo_blue "Pulling git..."
    git pull
    if [ $? -ne 0 ]; then
      echo_red "ERROR: git pull failed"
      exit 1
    else
      echo_green "OK : git pull succeeded"
    fi
  fi
}

do_apt_update() {
  if [ "$SKIP_APT" = false ]; then
    echo_blue "Updating APT and installing required packages.."
    bash ./install_required_apt_packages.sh
    if [ $? -ne 0 ]; then
      echo_red "ERROR: APT update and install failed"
      exit 1
    else
      echo_green "OK : APT update and install succeeded"
    fi
  fi
}

do_pip_req() {
  if [ "$SKIP_PIP_REQ" = false ]; then
    echo_blue "pip install requirements..."
    pip install -r ./requirements.txt
    if [ $? -ne 0 ]; then
      echo_red "ERROR: pip install requirements failed"
      exit 1
    else
      echo_green "OK : pip install requirements succeeded"
    fi
  fi
}

install_project_package() {
  if [ "$SKIP_PROJECT_PACKAGE" = true ]; then
    echo_blue "Skipping project package install"
    return
  fi
  echo_blue "Installing the project package..."
  pip install .
  if [ $? -ne 0 ]; then
    echo_red "ERROR: project package install failed"
    exit 1
  else
    echo_green "OK : project package install succeeded"
  fi
}
# ACTUAL SCRIPT LOGIC :

# Run the script logic inside a subshell
(

  activate_thecube_venv

  cd "$THECUBE_SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

  handle_arguments "$@"

  echo "SKIP_APT: $SKIP_APT"
  echo "SKIP_PIP_REQ: $SKIP_PIP_REQ"
  echo "SKIP_GIT: $SKIP_GIT"
  echo "SKIP_PROJECT_PACKAGE: $SKIP_PROJECT_PACKAGE"
  echo "DEBUG: $DEBUG"

  do_git_pull

  do_apt_update

  do_pip_req

  install_project_package

#  generate_cubebox_scripts_from_cubemaster_scripts

  copy_relevant_scripts_to_home

  setup_relevant_service

  echo_green "Update OK and done."

)
# End of subshell
