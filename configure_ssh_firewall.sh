#!/bin/bash

# Usage function
usage() {
    echo "Usage: $0 <subnet>"
    echo "Example: $0 192.168.1.0/24"
    echo "This script configures iptables to allow SSH access only from the specified subnet."
    exit 1
}

# Check for --help argument or no arguments
if [ "$1" == "--help" ] || [ "$#" -ne 1 ]; then
    usage
fi

# Validate the subnet argument
if [[ ! "$1" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]]; then
    echo "Error: Invalid subnet format."
    usage
fi

SUBNET=$1

# Add iptables rules
sudo iptables -A INPUT -p tcp -s "$SUBNET" --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j DROP

# Save the iptables rules
sudo sh -c "iptables-save > /etc/iptables/rules.v4"

# Create script to restore iptables rules on boot
sudo bash -c 'cat << EOF > /etc/network/if-pre-up.d/iptables
#!/bin/sh
iptables-restore < /etc/iptables/rules.v4
EOF'

# Make the script executable
sudo chmod +x /etc/network/if-pre-up.d/iptables

echo "iptables configured to allow SSH access only from $SUBNET"
