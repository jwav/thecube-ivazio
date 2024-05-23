"""Utility functions for the cube project"""
import datetime
import time
import subprocess
import os
import atexit
from typing import Optional, Union


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


def date_to_french_date_string(date: datetime.datetime,
                               weekday=True, day_number=True,month=True, year=True) -> Optional[str]:
    """Convert a datetime object to a string in a format like 'lundi 1 janvier 2021'"""
    # we need to specify the locale when calling strftimeto get the french version of the date. Don't modify the locale of the system
    import locale
    # Save the current locale
    current_locale = locale.getlocale(locale.LC_TIME)

    try:
        # Set the locale to French
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        # Format the date
        fmt_str = ""
        if weekday:
            fmt_str += '%A '
        if day_number:
            fmt_str += '%d '
        if month:
            fmt_str += '%B '
        if year:
            fmt_str += '%Y'
        french_date_string = date.strftime(fmt_str)
    except Exception as e:
        print(f"Error while converting {date} to french date string: {e}")
        return None
    finally:
        # Restore the original locale
        locale.setlocale(locale.LC_TIME, current_locale)
    return french_date_string

def hhmmss_string_to_seconds(hhmmss:str) -> Optional[int]:
    """Convert a string like 1h30m15s ,0h30, 01:32:55, 00:21 to the number of seconds it represents"""
    # find which characters are digits, which are not, and split the string using the non-digits as separators
    import itertools
    try:
        parts = ["".join(g) for k, g in itertools.groupby(hhmmss, key=str.isdigit)]
        # remove parts that are not pure digits
        parts = [part for part in parts if part.isdigit()]
        # convert the parts to integers
        parts = [int(part) for part in parts]
        # print(parts)
        # check the number of parts : 3 means hours, minutes, seconds, 2 means hours, seconds, 1 means seconds
        if len(parts) == 3:
            return parts[0]*3600 + parts[1]*60 + parts[2]
        elif len(parts) == 2:
            return parts[0]*3600 + parts[1]
        elif len(parts) == 1:
            return parts[0]
        else:
            raise ValueError("Invalid format for the time string")
    except Exception as e:
        print(f"Error while converting {hhmmss} to seconds: {e}")
        return None

def seconds_to_hhmmss_string(seconds: Union[float,int], separators="hms") -> str:
    """Convert a number of seconds to a string in the format HH:MM:SS using datetime"""
    sep1 = separators[0] if len(separators) > 0 else ""
    sep2 = separators[1] if len(separators) > 1 else ""
    sep3 = separators[2] if len(separators) > 2 else ""
    return time.strftime(f'%H{sep1}%M{sep2}%S{sep3}', time.gmtime(seconds))

def timestamp_to_french_date(timestamp: Union[float,int], weekday=True, day_number=True, month=True, year=True) -> str:
    """Convert a timestamp to a string in a format like 'lundi 1 janvier 2021'"""
    return date_to_french_date_string(datetime.datetime.fromtimestamp(timestamp),
                                      weekday=weekday, day_number=day_number, month=month, year=year)


if __name__ == "__main__":
    print("git branch version:", get_git_branch_version())
    print("git branch date:", get_git_branch_date())
    print("seconds_to_hhmmss_string(3600):", seconds_to_hhmmss_string(3600))
    print("date_to_french_date_string(datetime.datetime.now()):", date_to_french_date_string(datetime.datetime.now()))
    print("hhmmmsss_to_seconds('1h30m15s'):", hhmmss_string_to_seconds('1h30m15s'))
    print("hhmmmsss_to_seconds('0h30'):", hhmmss_string_to_seconds('0h30'))
    print("hhmmmsss_to_seconds('01:32:55'):", hhmmss_string_to_seconds('01:32:55'))
    print("hhmmmsss_to_seconds('00:21'):", hhmmss_string_to_seconds('00:21'))
    print("hhmmmsss_to_seconds('21'):", hhmmss_string_to_seconds('21'))
    print("seconds_to_hhmmss_string(3661):", seconds_to_hhmmss_string(3661))
    print("seconds_to_hhmmss_string(3661, separators='::'):", seconds_to_hhmmss_string(3661, separators='::'))
