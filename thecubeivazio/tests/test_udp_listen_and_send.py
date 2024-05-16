import socket
import threading
import time
import logging
import sys

class UDPServer:
    def __init__(self, ip: str, port: int, message: str):
        self.ip = ip
        self.port = port
        self.message = message
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self.sock.bind((self.ip, self.port))
        self.running = True

    def start(self):
        recv_thread = threading.Thread(target=self.receive_messages)
        recv_thread.start()

        send_thread = threading.Thread(target=self.send_messages)
        send_thread.start()

    def receive_messages(self):
        logging.info(f"Listening for UDP packets on {self.ip}:{self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)  # Buffer size is 1024 bytes
                logging.info(f"Received message from {addr}: {data.decode()}")
            except socket.error as e:
                logging.error(f"Socket error: {e}")
                self.running = False

    def send_messages(self):
        while self.running:
            try:
                self.sock.sendto(self.message.encode(), ('<broadcast>', self.port))
                logging.info(f"Sent message to broadcast:{self.port}: {self.message}")
            except socket.error as e:
                logging.error(f"Failed to send message: {e}")
            time.sleep(1)

    def stop(self):
        self.running = False
        self.sock.close()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        message = "hello"
    else:
        message = sys.argv[1]
    SERVER_IP = "0.0.0.0"  # Listen on all available interfaces
    SERVER_PORT = 5005

    server = UDPServer(SERVER_IP, SERVER_PORT, message)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        logging.info("Server has been stopped.")
