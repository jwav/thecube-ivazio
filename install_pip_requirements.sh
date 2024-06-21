# Get the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR" || exit 1
source "${SCRIPT_DIR}/venv/bin/activate"
echo "Activating virtual environment at ${SCRIPT_DIR}/venv/bin/activate"

echo "pip install requirements..."
pip install -r ./requirements.txt
if [ $? -ne 0 ]; then
  echo "ERROR: pip install requirements failed"
  exit 1
else
  echo "OK : pip install requirements succeeded"
fi

deactivate
echo "Deactivated virtual environment"