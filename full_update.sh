# Get the directory of the script
#SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# if the hostname contains "cube", use this defined directory
if [[ $(hostname) == *"cube"* ]]; then
  THECUBE_DIR="${HOME}/thecube-ivazio"
else
  THECUBE_DIR="/mnt/shared/thecube-ivazio"
fi

#cd "$SCRIPT_DIR" || exit 1
#source "${SCRIPT_DIR}/update_version.sh --full-update"
#cd "${THECUBE_DIR}" || exit 1
bash "${THECUBE_DIR}/update_version.sh" --full-update