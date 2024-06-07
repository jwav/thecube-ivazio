import socket
import threading
import time
from typing import Optional, Union


class CubeRgbMatrixContent:
    MATRIX_ID_SEPARATOR = "#"
    TEAM_NAME_END_TIMESTAMP_SEPARATOR = ">"
    def __init__(self, matrix_id: int, team_name: Optional[str], end_timestamp: Optional[float]):
        self.matrix_id = matrix_id
        self.team_name = team_name
        self.end_timestamp = end_timestamp

    @property
    def remaining_secs(self) -> float:
        try:
            return self.end_timestamp - time.time()
        except:
            return None

    @property
    def remaining_time_str(self) -> str:
        try:
            return time.strftime("%H:%M:%S", time.gmtime(self.remaining_secs))
        except:
            return ""

    def is_time_up(self) -> bool:
        try:
            return self.remaining_secs <= 0
        except:
            return False

    def is_blank(self) -> bool:
        return self.end_timestamp is None

    def to_string(self) -> str:
        tn = self.team_name or ""
        et = int(self.end_timestamp) or ""
        midsep = self.MATRIX_ID_SEPARATOR
        tensep = self.TEAM_NAME_END_TIMESTAMP_SEPARATOR
        return f"{self.matrix_id}{midsep}{tn}{tensep}{et}"

    @classmethod
    def make_from_string(cls, text: str) -> Optional['CubeRgbMatrixContent']:
        try:
            matrix_id, team_name_end_timestamp = text.split(cls.MATRIX_ID_SEPARATOR)
            team_name, end_timestamp = team_name_end_timestamp.split(cls.TEAM_NAME_END_TIMESTAMP_SEPARATOR)
            return cls(int(matrix_id), team_name, float(end_timestamp))
        except:
            return None


class CubeRgbMatrixContentDict(dict[int, CubeRgbMatrixContent]):
    SEPARATOR = "|"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return self.to_string()

    def to_string(self) -> str:
        return self.SEPARATOR.join([content.to_string() for content in self.values()])

    @classmethod
    def make_from_string(cls, text: str) -> 'CubeRgbMatrixContentDict':
        try:
            contents = [CubeRgbMatrixContent.make_from_string(content) for content in text.split(cls.SEPARATOR)]
            return cls({content.matrix_id: content for content in contents})
        except:
            return cls()


class CubeRgbServer:
    UDP_IP = "127.0.0.1"
    UDP_RGB_LISTEN_PORT = 5006
    UDP_MASTER_LISTEN_PORT = 5007
    UDP_BUFSIZE = 1024
    CELLS_SEPARATOR = "|"
    MSG_OK = "OK"
    MSG_ERROR = "ERROR"
    REPLY_TIMEOUT = 1

    def __init__(self, is_master=False, is_rgb=False):
        self.ip = self.UDP_IP
        if is_master and not is_rgb:
            self.listen_port = self.UDP_MASTER_LISTEN_PORT
            self.send_port = self.UDP_RGB_LISTEN_PORT
        elif is_rgb and not is_master:
            self.listen_port = self.UDP_RGB_LISTEN_PORT
            self.send_port = self.UDP_MASTER_LISTEN_PORT
        else:
            raise ValueError("CubeRgbServer : is_master and is_rgb cannot be both True or both False")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting

        self._thread_listen = threading.Thread(target=self._listen_loop)
        self._thread_listen.daemon = True
        self._keep_listening = False

        self._last_text_received: str = ""
        # dict of CubeRgbMatrixContent objects, indexed by matrix_id
        self._rgb_matrix_contents_dict = CubeRgbMatrixContentDict()
        self._lock = threading.Lock()
        self._debug = False

        self.start_listening()

    # if debug is true, behaves like print but precedes the message with the class name and its port
    def _print(self, *args, **kwargs):
        if self._debug:
            print(f"{self.__class__.__name__}({self.listen_port}):", *args, **kwargs)

    def start_listening(self):
        self._sock.bind((self.UDP_IP, self.listen_port))
        self._keep_listening = True
        self._thread_listen.start()

    def _listen_loop(self):
        while self._keep_listening:
            data, addr = self._sock.recvfrom(self.UDP_BUFSIZE)
            with self._lock:
                self._last_text_received = data.decode()
            self._print(f"Received message: '{self._last_text_received}' from {addr}")
            try:
                d = CubeRgbMatrixContentDict.make_from_string(self._last_text_received)
                if not d:
                    continue
                self._rgb_matrix_contents_dict.update(d)
                self._print(f"Updated rgb_matrix_contents_dict: {self._rgb_matrix_contents_dict}")
                self._send_text(self.MSG_OK)
            except Exception as e:
                self._print(f"Error updating rgb_matrix_contents_dict: {e}")
                self._send_text(self.MSG_ERROR)

    def wait_for_ok(self, timeout=None) -> Optional[bool]:
        timeout = timeout or self.REPLY_TIMEOUT
        end_time = time.time() + timeout
        while True:
            if time.time() > end_time:
                return None
            text = self.get_last_text_received()
            if text == self.MSG_OK:
                return True
            elif text == self.MSG_ERROR:
                return False
            time.sleep(0.1)

    def stop_listening(self):
        self._print("Stopping listening...")
        self._keep_listening = False
        self._thread_listen.join(timeout=0.1)
        self._sock.close()
        self._print("Stopped listening")

    def _send_text(self, text: str) -> bool:
        try:
            self._print(f"Sending message '{text}' to {self.UDP_IP}:{self.send_port}")
            result = self._sock.sendto(text.encode(), (self.UDP_IP, self.send_port))
            assert result == len(text)
            # self._print(f"Sent message '{text}' to {self.UDP_IP}:{self.send_port}")
            return True
        except Exception as e:
            self._print(f"Error sending message '{text}' to {self.UDP_IP}:{self.send_port}: {e}")
            return False

    def send_rgb_matrix_contents_dict(self, rmcd: CubeRgbMatrixContentDict) -> bool:
        try:
            while True:
                assert self._send_text(rmcd.to_string())
                if self.wait_for_ok():
                    return True
                time.sleep(0.1)
                self._print(f"No OK received. Retrying sending rgb_matrix_contents_dict")
        except Exception as e:
            self._print(f"Error sending rgb_matrix_contents_dict: {e}")
            return False

    def get_last_text_received(self) -> str:
        with self._lock:
            return self._last_text_received

    def get_rgb_matrix_contents(self) -> CubeRgbMatrixContentDict:
        with self._lock:
            return self._rgb_matrix_contents_dict


# Example usage
if __name__ == "__main__":
    master = CubeRgbServer(is_master=True)
    rgb_server = CubeRgbServer(is_rgb=True)
    master._debug = True
    rgb_server._debug = True

    # send some content
    contents_dict = CubeRgbMatrixContentDict({
        0: CubeRgbMatrixContent(0, "team1", time.time() + 10),
        1: CubeRgbMatrixContent(1, "team2", time.time() + 20),
        2: CubeRgbMatrixContent(2, "team3", time.time() + 30),
    })

    master.send_rgb_matrix_contents_dict(contents_dict)

    rgb_server.stop_listening()
    master.stop_listening()
