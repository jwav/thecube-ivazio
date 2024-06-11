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
            if self.end_timestamp is None:
                return None
            if self.is_time_up():
                return 0
            return self.end_timestamp - time.time()
        except:
            return None

    @property
    def remaining_time_str(self) -> str:
        try:
            if self.end_timestamp is None:
                return ""
            elif self.is_time_up():
                return "00:00:00"
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

    def __repr__(self):
        return self.to_string()

    def to_string(self) -> str:
        try:
            tn = self.team_name or ""
            try: et = int(self.end_timestamp)
            except: et = ""
            midsep = self.MATRIX_ID_SEPARATOR
            tensep = self.TEAM_NAME_END_TIMESTAMP_SEPARATOR
            return f"{self.matrix_id}{midsep}{tn}{tensep}{et}"
        except Exception as e:
            print(f"Error in CubeRgbMatrixContent.to_string: {e}")
            return ""

    @classmethod
    def make_from_string(cls, text: str) -> Optional['CubeRgbMatrixContent']:
        try:
            matrix_id, team_name_end_timestamp = text.split(cls.MATRIX_ID_SEPARATOR)
            team_name, end_timestamp = team_name_end_timestamp.split(cls.TEAM_NAME_END_TIMESTAMP_SEPARATOR)
            try: end_timestamp = float(end_timestamp)
            except: end_timestamp = None
            return cls(int(matrix_id), team_name, end_timestamp)
        except Exception as e:
            print(f"Error in CubeRgbMatrixContent.make_from_string: {e}")
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
        except Exception as e:
            print(f"Error in CubeRgbMatrixContentDict.make_from_string: {e}")
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

    def __init__(self, is_master=False, is_rgb=False, debug=False):
        self._debug = debug

        self.ip = self.UDP_IP
        if is_master and not is_rgb:
            self.listen_port = self.UDP_MASTER_LISTEN_PORT
            self.send_port = self.UDP_RGB_LISTEN_PORT
            self.name = "CubeRgbServer-Master"
        elif is_rgb and not is_master:
            self.listen_port = self.UDP_RGB_LISTEN_PORT
            self.send_port = self.UDP_MASTER_LISTEN_PORT
            self.name = "CubeRgbServer-RGB"
        else:
            raise ValueError("CubeRgbServer : is_master and is_rgb cannot be both True or both False")
        self._print(f"CubeRgbServer : is_master={is_master}, is_rgb={is_rgb}, listen_port={self.listen_port}, send_port={self.send_port}")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting

        self._thread_listen = threading.Thread(target=self._listen_loop, daemon=True)
        self._keep_listening = False

        self._last_text_received: str = ""
        # dict of CubeRgbMatrixContent objects, indexed by matrix_id
        self._rgb_matrix_contents_dict = CubeRgbMatrixContentDict()
        self._lock = threading.Lock()

        self.start_listening()
        self._print(f"Finished initializing")

    # if debug is true, behaves like print but precedes the message with the class name and its port
    def _print(self, *args, **kwargs):
        if self._debug:
            # print(f"{self.__class__.__name__}({self.listen_port}):", *args, **kwargs)
            print(f"{self.name}({self.listen_port}):", *args, **kwargs)


    def start_listening(self):
        try:
            self._sock.bind((self.UDP_IP, self.listen_port))
            self._keep_listening = True
            self._thread_listen.start()
            self._print("Started listening")
        except Exception as e:
            self._print(f"Error starting listening: {e}")

    def _listen_loop(self):
        while self._keep_listening:
            data, addr = self._sock.recvfrom(self.UDP_BUFSIZE)
            text = data.decode()
            self._print(f"Received message: '{text}' from {addr}")
            self._handle_received_text(text)

    def _handle_received_text(self, text:str)->bool:
        try:
            self._print(f"Handling received text: {text}")
            with self._lock:
                self._last_text_received = text
            if text in (self.MSG_OK, self.MSG_ERROR):
                return True
            d = CubeRgbMatrixContentDict.make_from_string(text)
            if not d:
                self._print(f"Error decoding rgb_matrix_contents_dict: {text}")
                return False
            self._rgb_matrix_contents_dict.update(d)
            self._print(f"Updated rgb_matrix_contents_dict: {self._rgb_matrix_contents_dict}")
            # display the first content to check
            for matrix_id, content in self._rgb_matrix_contents_dict.items():
                self._print(f"Displaying first content")
                self._print(f"matrix_id: {matrix_id}, content: {content}, end_timestamp: {content.end_timestamp}")
                self._print(f"remaining_secs: {content.remaining_secs}, remaining_time_str: {content.remaining_time_str}")
                break
            self._send_text(self.MSG_OK)
        except Exception as e:
            self._print(f"Error in _handle_received_str({text}): {e}")
            self._send_text(self.MSG_ERROR)
            return False

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

    def send_rgb_matrix_contents_dict(self, rmcd: CubeRgbMatrixContentDict, nbtries=5) -> bool:
        try:
            for tryid in range(nbtries):
                assert self._send_text(rmcd.to_string())
                if self.wait_for_ok():
                    return True
                time.sleep(0.1)
                self._print(f"Retrying send_rgb_matrix_contents_dict, try {tryid + 1}/{nbtries}")
            self._print(f"Failed to send rgb_matrix_contents_dict after {nbtries} tries")
            return False
        except Exception as e:
            self._print(f"Error sending rgb_matrix_contents_dict: {e}")
            return False

    def get_last_text_received(self) -> str:
        with self._lock:
            return self._last_text_received

    def get_rgb_matrix_contents_dict(self) -> CubeRgbMatrixContentDict:
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
