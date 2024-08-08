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

copy_relevant_scripts_to_home() {
   # Initialize an array for scripts to copy
   local scripts_to_copy=(
     "activate_venv.sh"
     "*thecube*.sh"
     "configure_ssh_firewall.sh"
   )

   # Initialize an array for the filtered scripts
   local filtered_scripts=()

   # Function to add scripts based on pattern
   add_scripts() {
     local pattern=$1
     for file in $pattern; do
       if [[ -f $file ]]; then
         filtered_scripts+=("$file")
       fi
     done
   }

   # Add the general scripts
   for script in "${scripts_to_copy[@]}"; do
     add_scripts $script
   done

   # Copy and chmod+x the filtered scripts
   for script in "${filtered_scripts[@]}"; do
     echo_blue "Copying $script to home directory and making it executable."
     cp "$script" ~/
     chmod +x ~/"$script"
   done
 }


setup_relevant_service() {
  setup_thecube_service
  if [ $? -ne 0 ]; then
    echo_red "ERROR: setup_thecube_service failed"
    return 1
  else
    echo_green "OK : setup_thecube_service succeeded"
  fi
  return 0
}

chmodx_scripts(){
  echo_blue "Making all .sh files in the current directory executable..."
  # all .sh files in the current directory
  for file in *.sh; do
    chmod +x "$file"
  done
  if [ $? -ne 0 ]; then
    echo_red "ERROR: chmod +x failed"
    return 1
  else
    echo_green "OK : chmod +x succeeded"
  fi
  return 0
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
  if [ "$SKIP_GIT" = true ]; then
    echo_blue "Skipping git pull"
    return 0
  fi
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
  return 0
}

do_apt_update() {
  if [ "$SKIP_APT" = true ]; then
    echo_blue "Skipping APT update and install"
    return 0
  fi
  echo_blue "Updating APT and installing required packages.."
  bash ./install_required_apt_packages.sh
  if [ $? -ne 0 ]; then
    echo_red "ERROR: APT update and install failed"
    return 1
  else
    echo_green "OK : APT update and install succeeded"
  fi
  return 0
}

do_pip_req() {
  if [ "$SKIP_PIP_REQ" = true ]; then
    echo_blue "Skipping pip install requirements"
    return 0
  fi
  echo_blue "pip install requirements..."
  pip install -r ./requirements.txt
  if [ $? -ne 0 ]; then
    echo_red "ERROR: pip install requirements failed"
    return 1
  else
    echo_green "OK : pip install requirements succeeded"
  fi
  return 0
}

install_project_package() {
  if [ "$SKIP_PROJECT_PACKAGE" = true ]; then
    echo_blue "Skipping project package install"
    return 0
  fi
  echo_blue "Installing the project package..."
  pip install .
  if [ $? -ne 0 ]; then
    echo_red "ERROR: project package install failed"
    exit 1
  else
    echo_green "OK : project package install succeeded"
  fi
  return 0
}
# ACTUAL SCRIPT LOGIC :

# Run the script logic inside a subshell
(

  activate_thecube_venv

  cd "$THECUBE_SCRIPT_DIR" || exit 1
  echo "Current working directory: $(pwd)"

  handle_arguments "$@" || exit 1

  echo "SKIP_APT: $SKIP_APT"
  echo "SKIP_PIP_REQ: $SKIP_PIP_REQ"
  echo "SKIP_GIT: $SKIP_GIT"
  echo "SKIP_PROJECT_PACKAGE: $SKIP_PROJECT_PACKAGE"
  echo "DEBUG: $DEBUG"

  do_git_pull || exit 1

  do_apt_update || exit 1

  do_pip_req || exit 1

  install_project_package || exit 1

  chmodx_scripts || exit 1

  copy_relevant_scripts_to_home || exit 1

  setup_relevant_service || exit 1

  echo_green "Update OK and done."

)
# End of subshell
