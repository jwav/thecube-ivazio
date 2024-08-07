"""Utility functions for the cube project"""
import atexit
import base64
import datetime
import json
import re
import subprocess
import time
from typing import List

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from thecubeivazio.cube_common_defines import *


def is_raspberry_pi() -> bool:
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        if 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo:
            return True
    except FileNotFoundError:
        return False
    return False


def is_windows() -> bool:
    return os.name == 'nt'


def get_git_branch_version() -> str:
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


def get_git_branch_date() -> str:
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
    ENVIRON_DISPLAY = ":1"

    @classmethod
    def is_x_server_already_running(cls):
        return cls._is_x_server_running()

    @classmethod
    def _is_this_system_a_cubebox(cls):
        """Check if this system is a CubeBox"""
        return "cubebox" in get_system_hostname()

    @classmethod
    def _is_x_server_running(cls):
        try:
            # Check if X or Xvfb processes are running
            x_process = subprocess.run(["pgrep", "-x", "X"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            xvfb_process = subprocess.run(["pgrep", "-x", "Xvfb"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            print(f"pgrep X returncode: {x_process.returncode}")
            print(f"pgrep X output: {x_process.stdout.decode().strip()}")
            print(f"pgrep Xvfb returncode: {xvfb_process.returncode}")
            print(f"pgrep Xvfb output: {xvfb_process.stdout.decode().strip()}")

            if x_process.returncode == 0 or xvfb_process.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    @classmethod
    def old_has_x_server(cls):
        """NOTE: this method doesn't work!
        Check if an X server or Wayland server is running on the machine.
        Return True if it is, False otherwise."""
        try:
            print("Checking for X server...")
            result = subprocess.run(['xdpyinfo'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    check=True)
            print("X server is running. xdpyinfo output:", result.stdout.decode())
            return True
        except subprocess.CalledProcessError as e:
            print("xdpyinfo returned an error:", e.stderr.decode())
            print("X server is not running.")
        except FileNotFoundError:
            print("xdpyinfo not found. Ensure it is installed.")

        # Check for Wayland
        if 'WAYLAND_DISPLAY' in os.environ:
            print("Wayland server is running.")
            return True

        print("No display server is running.")
        return False

    @classmethod
    def start_xvfb(cls, force_start=False):
        if cls.is_x_server_already_running() and not force_start:
            print("X server is already running. Not starting.")
            return
        # Start Xvfb on display :1 with screen 0
        xvfb_cmd = ['Xvfb', cls.ENVIRON_DISPLAY, '-screen', '0', '1024x768x16']
        cls.xvfb_process = subprocess.Popen(xvfb_cmd)
        print(f"Started Xvfb on display {cls.ENVIRON_DISPLAY}")
        # Set the DISPLAY environment variable to use the virtual display
        os.environ['DISPLAY'] = cls.ENVIRON_DISPLAY
        # register terminate_xvfb to be called at exit
        atexit.register(cls.terminate_xvfb)

    @classmethod
    def terminate_xvfb(cls):
        try:
            # Terminate the Xvfb process
            cls.xvfb_process.terminate()
            print("Terminated Xvfb")
        except AttributeError:
            print("Xvfb process not found")


class CubeSimpleTimer:
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
                               weekday=True, day_number=True, month=True, year=True) -> Optional[str]:
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


def hhmmss_string_to_seconds_alternative(hhmmss: str) -> Optional[int]:
    """Convert a string like 1h30m15s, 0h30, 01:32:55, 00:21 to the number of seconds it represents"""
    try:
        # Split the string by non-digit characters
        parts = re.split(r'\D+', hhmmss)
        parts = [part for part in parts if part]  # Remove empty strings

        # Check the number of parts and convert accordingly
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
        elif len(parts) == 2:
            hours, minutes = map(int, parts)
            seconds = 0
        elif len(parts) == 1:
            hours = int(parts[0])
            minutes = 0
            seconds = 0
        else:
            raise ValueError("Invalid format for the time string")

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    except Exception as e:
        print(f"Error while converting {hhmmss} to seconds: {e}")
        return None


def hhmmss_string_to_seconds(hhmmss: str) -> Optional[int]:
    """Convert a string like 1h30m15s, 0h30m, 01:32:55, 00:21 to the number of seconds it represents"""
    try:
        hhmmss = hhmmss.lower()

        if 'h' in hhmmss or 'm' in hhmmss or 's' in hhmmss:
            pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
            match = pattern.match(hhmmss)
            if not match:
                raise ValueError("Invalid format for the time string")
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
        else:
            parts = hhmmss.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
            elif len(parts) == 2:
                hours = 0
                minutes, seconds = map(int, parts)
            elif len(parts) == 1:
                hours = 0
                minutes = 0
                seconds = int(parts[0])
            else:
                raise ValueError("Invalid format for the time string")

        # Handle case like '1h30' where '30' is interpreted as minutes
        if 'h' in hhmmss and 'm' not in hhmmss and 's' not in hhmmss:
            hours = int(hhmmss.split('h')[0])
            minutes = int(hhmmss.split('h')[1])
            seconds = 0

        total_seconds = hours * 3600 + minutes * 60 + seconds
        return total_seconds
    except Exception as e:
        print(f"Error while converting {hhmmss} to seconds: {e}")
        return None


# TODO: test
def seconds_to_hhmmss_string(seconds: Seconds, separators: Union[str, List[str]] = "hms",
                             hours=True, mins=True, secs=True) -> str:
    """Convert a number of seconds to a string in the format HH:MM:SS using datetime"""
    try:
        if isinstance(separators, str):
            separators = list(separators)
        sep1 = separators[0] if len(separators) > 0 else ""
        sep2 = separators[1] if len(separators) > 1 else ""
        sep3 = separators[2] if len(separators) > 2 else ""
        h = "%H" if hours else ""
        m = "%M" if mins else ""
        s = "%S" if secs else ""
        return time.strftime(f'{h}{sep1}{m}{sep2}{s}{sep3}', time.gmtime(seconds))
    except Exception as e:
        return "??:??:??"


# TODO: test
def timestamp_to_hhmmss_time_of_day_string(timestamp: Timestamp, separators="hms",
                                           hours=True, mins=True, secs=True) -> str:
    """Convert a timestamp to a time of day string in the format HH:MM:SS using datetime
    (i.e. it cannot go beyond 23:59:59)"""
    # use datetime to get the time of the timestamp
    try:
        time_of_day = datetime.datetime.fromtimestamp(timestamp).time()
        sep1 = separators[0] if len(separators) > 0 else ""
        sep2 = separators[1] if len(separators) > 1 else ""
        sep3 = separators[2] if len(separators) > 2 else ""
        h = "%H" if hours else ""
        m = "%M" if mins else ""
        s = "%S" if secs else ""
        return time_of_day.strftime(f'{h}{sep1}{m}{sep2}{s}{sep3}')
    except Exception as e:
        return "??:??:??"


def timestamp_to_french_date(timestamp: Union[float, int], weekday=True, day_number=True, month=True, year=True) -> str:
    """Convert a timestamp to a string in a format like 'lundi 1 janvier 2021'"""
    try:
        return date_to_french_date_string(datetime.datetime.fromtimestamp(timestamp),
                                          weekday=weekday, day_number=day_number, month=month, year=year)
    except Exception as e:
        return ""


def timestamp_to_date(timestamp: Union[float, int], separator="/") -> str:
    """Convert a timestamp to a string in a dd/mm/yyyy format"""
    # noinspection PyBroadException
    try:
        date = datetime.datetime.fromtimestamp(timestamp)
        return date.strftime(f"%d{separator}%m{separator}%Y")
    except Exception as e:
        return "??/??/????"


def get_system_hostname() -> str:
    """Get the hostname of the running machine"""
    # noinspection PyBroadException
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "hostnameNone"


def timestamps_are_in_same_day(timestamp1: float, timestamp2: float) -> bool:
    """Check if two timestamps are in the same day"""
    # use datetime to get the date of the timestamps
    date1 = datetime.datetime.fromtimestamp(timestamp1)
    date2 = datetime.datetime.fromtimestamp(timestamp2)
    return date1.date() == date2.date()


def timestamps_are_in_same_week(timestamp1: float, timestamp2: float) -> bool:
    """Check if two timestamps are in the same week"""
    # use datetime to get the date of the timestamps
    date1 = datetime.datetime.fromtimestamp(timestamp1)
    date2 = datetime.datetime.fromtimestamp(timestamp2)
    return date1.isocalendar()[1] == date2.isocalendar()[1]


def timestamps_are_in_same_month(timestamp1: float, timestamp2: float) -> bool:
    """Check if two timestamps are in the same month"""
    # use datetime to get the date of the timestamps
    date1 = datetime.datetime.fromtimestamp(timestamp1)
    date2 = datetime.datetime.fromtimestamp(timestamp2)
    return date1.month == date2.month


def today_start_timestamp(timestamp: float = None):
    """Get the timestamp of the start of the day of the timestamp"""
    if timestamp is None:
        timestamp = time.time()
    # use datetime to get the date of the timestamp
    date = datetime.datetime.fromtimestamp(timestamp)
    # create a new datetime object with the same year, month and day, but at 00:00:00
    start_date = datetime.datetime(date.year, date.month, date.day)
    return start_date.timestamp()


def this_week_start_timestamp(timestamp: float = None):
    """Get the timestamp of the start of the week of the timestamp"""
    if timestamp is None:
        timestamp = time.time()
    # use datetime to get the date of the timestamp
    date = datetime.datetime.fromtimestamp(timestamp)
    # get the number of the week
    week_number = date.isocalendar()[1]
    # get the year
    year = date.year
    # create a new datetime object with the same year, month and day, but at 00:00:00
    start_date = datetime.datetime.strptime(f"{year}-{week_number}-1", "%Y-%W-%w")
    return start_date.timestamp()


def one_week_ago_start_timestamp(timestamp: float = None):
    """Get the timestamp of 7 days ago exactly" """
    if timestamp is None:
        timestamp = time.time()
    return timestamp - 7 * 24 * 3600


def this_month_start_timestamp(timestamp: float = None):
    """Get the timestamp of the start of the month of the timestamp"""
    if timestamp is None:
        timestamp = time.time()
    # use datetime to get the date of the timestamp
    date = datetime.datetime.fromtimestamp(timestamp)
    # create a new datetime object with the same year and month, but at 00:00:00 on the first day of the month
    start_date = datetime.datetime(date.year, date.month, 1)
    return start_date.timestamp()


def this_year_start_timestamp(timestamp: float = None):
    """Get the timestamp of the start of the year of the timestamp"""
    if timestamp is None:
        timestamp = time.time()
    # use datetime to get the date of the timestamp
    date = datetime.datetime.fromtimestamp(timestamp)
    # create a new datetime object with the same year, but at 00:00:00 on the first day of the year
    start_date = datetime.datetime(date.year, 1, 1)
    return start_date.timestamp()


def int_ms_to_float_sec(ms: int) -> float:
    return ms / 1000.0

def float_sec_to_int_ms(sec: float) -> int:
    return int(sec * 1000)

def now_ms() -> int:
    return int(time.time() * 1000)

def float_eq(a: float, b: float, epsilon: float = 0.001) -> bool:
    return abs(a - b) < epsilon

def generate_encryption_key(password: str) -> bytes:
    # Derive a key from the password without using a salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"",  # Empty salt
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_string_to_str(string: str, password: str) -> str:
    return encrypt_string_to_bytes(string, password).decode()


def encrypt_string_to_bytes(string: str, password: str) -> bytes:
    key = generate_encryption_key(password)
    fernet = Fernet(key)
    encrypted_bytes = fernet.encrypt(string.encode())
    return encrypted_bytes


def decrypt_string(encrypted_string: str, password: str) -> str:
    key = generate_encryption_key(password)
    fernet = Fernet(key)
    decrypted_string = fernet.decrypt(encrypted_string.encode())
    return decrypted_string.decode()


@cubetry
def encrypt_and_write_to_file(str_to_encrypt: str, filepath: str, password: str) -> bool:
    """Encrypt the string str_to_encrypt using the password and write it to the file at file_path."""
    with open(filepath, 'wb') as f:
        encrypted_data = encrypt_string_to_bytes(str_to_encrypt, password)
        f.write(encrypted_data)
    return True


@cubetry
def read_encrypted_file(filepath: str, password: str) -> str:
    """Decrypt the file at file_path using the provided key."""
    with open(filepath, 'rb') as f:
        encrypted_data = f.read()
        key = generate_encryption_key(password)
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data.decode()


def validate_json(json_str):
    try:
        json_obj = json.loads(json_str)
        return True, None
    except json.JSONDecodeError as e:
        return False, str(e)


def str_to_bool(s: str) -> bool:
    return s.lower() in ['true', '1']


@cubetry
def reboot():
    """Reboot the system"""
    subprocess.run(['sudo', 'reboot'])
    return True

@cubetry
def stty_sane():
    """Set the terminal to a sane state"""
    subprocess.run(['stty', 'sane'])
    return True

###########
# TESTS
##########

def test_time_conversions():
    test_cases = [
        ('1h30m15s', 5415),
        ('0h30m', 1800),
        ('1h30', 5400),
        ('01:32:55', 5575),
        ('00:21', 21),
        ('21', 21)
    ]

    for hhmmss, expected in test_cases:
        result = hhmmss_string_to_seconds(hhmmss)
        print(f"Input string: {hhmmss}")
        print(f"Expected: {expected}, Got: {result}")
        assert result == expected


def test_utils():
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
    print("timestamp_to_french_date(time.time()):", timestamp_to_french_date(time.time()))
    print("timestamp_to_date(time.time()):", timestamp_to_date(time.time()))
    print("get_system_hostname():", get_system_hostname())
    print(f"is raspberry pi? {is_raspberry_pi()}")
    print("timestamps_are_in_same_day(time.time(), time.time()):", timestamps_are_in_same_day(time.time(), time.time()))
    print("timestamps_are_in_same_day(time.time(), time.time() - 86400):",
          timestamps_are_in_same_day(time.time(), time.time() - 864000))
    print("timestamps_are_in_same_week(time.time(), time.time()):",
          timestamps_are_in_same_week(time.time(), time.time()))
    print("timestamps_are_in_same_week(time.time(), time.time() - 86400):",
          timestamps_are_in_same_week(time.time(), time.time() - 864000))
    print("timestamps_are_in_same_month(time.time(), time.time()):",
          timestamps_are_in_same_month(time.time(), time.time()))
    print("timestamps_are_in_same_month(time.time(), time.time() - 86400):",
          timestamps_are_in_same_month(time.time(), time.time() - 864000))
    print("today_start_timestamp():", today_start_timestamp())
    print("this_week_start_timestamp():", this_week_start_timestamp())
    print("this_month_start_timestamp():", this_month_start_timestamp())
    print("encrypt_string('test', 'password'):", encrypt_string_to_str('test', 'password'))
    print("decrypt_string(encrypt_string('test', 'password'), 'password'):",
          decrypt_string(encrypt_string_to_str('test', 'password'), 'password'))


if __name__ == "__main__":
    test_time_conversions()
    exit(0)
    test_utils()
