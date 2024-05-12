"""Utility functions for the cube project"""

import time
import subprocess
import os
import atexit



def get_git_branch_version():
    """
    Get the current git branch and commit hash
    """
    import subprocess
    try:
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode()
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode()
        return f"{branch} {commit}"
    except subprocess.CalledProcessError:
        return "Unknown"


def get_git_branch_date():
    """
    Get the date of the last commit on the current branch
    """
    import subprocess
    try:
        date = subprocess.check_output(['git', 'show', '-s', '--format=%ci']).strip().decode()
        return date
    except subprocess.CalledProcessError:
        return "Unknown"


class XvfbManager:
    """static class handling the Xvfb virtual display in case we're running without X and some module needs it"""
    xvfb_process = None

    @staticmethod
    def has_x_server():
        """Check if an X server is running on the machine. Return True if it is, False otherwise."""
        try:
            # Try to run `xdpyinfo` to check for an X server
            subprocess.run(['xdpyinfo'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print("X server is running.")
            return True
        except subprocess.CalledProcessError:
            print("X server is not running.")
            return False

    @staticmethod
    def start_xvfb():
        # Start Xvfb on display :1 with screen 0
        xvfb_cmd = ['Xvfb', ':1', '-screen', '0', '1024x768x16']
        XvfbManager.xvfb_process = subprocess.Popen(xvfb_cmd)
        print("Started Xvfb on display :1")
        # Set the DISPLAY environment variable to use the virtual display
        os.environ['DISPLAY'] = ':1'
        # register terminate_xvfb to be called at exit
        atexit.register(XvfbManager.terminate_xvfb)

    @staticmethod
    def terminate_xvfb():
        try:
            # Terminate the Xvfb process
            XvfbManager.xvfb_process.terminate()
            print("Terminated Xvfb")
        except AttributeError:
            print("Xvfb process not found")


class SimpleTimer:
    def __init__(self, timeout):
        self.timeout = timeout
        self.start_time = time.time()

    def is_timeout(self):
        return time.time() - self.start_time >= self.timeout

    def reset(self):
        self.start_time = time.time()

    def timer(self):
        return time.time() - self.start_time


if __name__ == "__main__":
    print("git branch version:", get_git_branch_version())
    print("git branch date:", get_git_branch_date())
