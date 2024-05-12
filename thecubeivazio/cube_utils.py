"""Utility functions for the cube project"""

import time

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