#!/usr/bin/env bash

this_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${this_script_dir}/thecube_common_defines.sh" || {
  echo "ERROR: Could not load thecube_common_defines.sh"
  exit 1
}

# Set audio output to 3.5mm jack using ALSA
amixer cset numid=3 1

# Check if PulseAudio is running and set the default sink to 3.5mm jack
if pgrep -x "pulseaudio" >/dev/null; then
  pactl set-default-sink 0
else
  echo "PulseAudio is not running."
fi

# Verify the ALSA setting
echo "ALSA audio output set to:"
amixer cget numid=3

# Verify the PulseAudio setting
if pgrep -x "pulseaudio" >/dev/null; then
  echo "PulseAudio default sink set to:"
  pactl info | grep "Default Sink"
else
  echo "PulseAudio is not running, skipping PulseAudio check."
fi

sudo usermod -aG audio ivazio

# Stop PulseAudio and kill any running instances
pulseaudio --kill

# Remove old PulseAudio PID files
rm -f ~/.config/pulse/*pid

# Restart PulseAudio
systemctl --user restart pulseaudio

# Stop and restart ALSA service
sudo systemctl restart alsa-state

# Reload ALSA settings
sudo alsactl restore

# Test the audio output
#echo "Testing audio output through 3.5mm jack..."
#speaker-test -t wav -c 2
