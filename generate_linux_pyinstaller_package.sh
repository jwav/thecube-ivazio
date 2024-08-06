# Remove existing dist directory
if [ -d "dist" ]; then
  rm -rf dist
fi

# Set environment variable to enable console or not
export CUBEGUI_ENABLE_CONSOLE=True

# Generate the PyInstaller package
pyinstaller thecubeivazio/cubegui/cubegui_pyinstaller.spec
