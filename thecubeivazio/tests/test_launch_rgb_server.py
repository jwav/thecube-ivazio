import subprocess
import time

# Start the process
process = subprocess.Popen(['sudo', 'python3', '/home/ivazio/thecube-ivazio/thecubeivazio/cube_rgbmatrix_server.py'])

# Wait for a specified amount of time (e.g., 10 seconds)
time.sleep(5)

# Stop the process
process.terminate()

# Optionally wait for the process to clean up
process.wait()
