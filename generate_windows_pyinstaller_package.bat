rem Remove existing dist directory
if exist dist (
    rmdir /s /q dist
)

rem Set environment variable to enable console or not
set "CUBEGUI_ENABLE_CONSOLE=True"

rem Generate the PyInstaller package
pyinstaller thecubeivazio\cubegui\cubegui.spec
