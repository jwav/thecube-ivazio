#!/usr/bin/env bash

source "/home/ivazio/thecube-ivazio/thecube_common_defines.sh" || source "/mnt/shared/thecube-ivazio/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

REMOTE_SCRIPT=""
REMOTE_COMMAND=""
USERNAME="ivazio"

handle_args() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --script)
                REMOTE_SCRIPT="$2"
                shift
                ;;
            --command)
                REMOTE_COMMAND="$2"
                shift
                ;;
            *)
                echo_red "Unknown parameter: $1"
                exit 1
                ;;
        esac
        shift
    done

    # Ensure either --script or --command is provided
    if [ -z "$REMOTE_SCRIPT" ] && [ -z "$REMOTE_COMMAND" ]; then
        echo_red "Usage: $0 --script /path/to/remote_script.sh or --command \"command to execute\""
        exit 1
    fi

    # Ensure the remote script exists if provided
    if [ -n "$REMOTE_SCRIPT" ] && [ ! -f "$REMOTE_SCRIPT" ]; then
        echo_red "Error: Script $REMOTE_SCRIPT not found."
        exit 1
    fi
}

# Handle the arguments
handle_args "$@"

# List of servers
servers=(cubebox1.local cubebox2.local cubebox3.local cubebox4.local cubebox5.local cubebox6.local cubebox7.local cubebox8.local cubebox9.local cubebox10.local cubebox11.local cubebox12.local)

# Display confirmation message
if [ -n "$REMOTE_SCRIPT" ]; then
    echo_blue "The following script will be executed on the listed servers:"
    echo_blue "Script: $REMOTE_SCRIPT"
else
    echo_blue "The following command will be executed on the listed servers:"
    echo_blue "Command: $REMOTE_COMMAND"
fi
echo_blue "Servers:"
for server in "${servers[@]}"; do
    echo_blue "- $server"
done

# Prompt for confirmation
read -p "Do you want to proceed? (y/n) " confirmation
if [[ "$confirmation" != "y" ]]; then
    echo_red "Execution cancelled."
    exit 0
fi

# Loop through each server and execute the script or command
for server in "${servers[@]}"
do
    if [ -n "$REMOTE_SCRIPT" ]; then
        echo_blue "Executing script on $server"
        ssh "$USERNAME"@$server "bash -s" < "$REMOTE_SCRIPT"
    else
        echo_blue "Executing command on $server"
        ssh "$USERNAME"@$server "$REMOTE_COMMAND"
    fi

    if [ $? -ne 0 ]; then
        echo_red "Failed to execute on $server"
    else
        echo_green "Successfully executed on $server"
    fi
done
