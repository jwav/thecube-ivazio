import logging
import socket


class UDPServer:
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.sock = None
        self.log = logging.getLogger(__name__)

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self.sock.bind((self.ip, self.port))
        self.log.info(f"Listening for UDP packets on {self.ip}:{self.port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(1024)  # Buffer size is 1024 bytes
                self.log.info(f"Received message from {addr}: {data.decode()}")
        except KeyboardInterrupt:
            self.log.info("Server shutting down...")
        finally:
            self.close()

    def close(self):
        if self.sock:
            self.sock.close()
            self.log.info("Socket closed.")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SERVER_IP = "0.0.0.0"  # Listen on all available interfaces
    SERVER_PORT = 5005
    server = UDPServer(SERVER_IP, SERVER_PORT)
    server.start()