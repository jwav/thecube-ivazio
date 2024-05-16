import socket
import time

def send_udp_packets(ip: str, port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        while True:
            message = "hello"
            sock.sendto(message.encode(), (ip, port))
            print(f"Sent message to {ip}:{port}: {message}")
            time.sleep(1)

# Example usage
if __name__ == "__main__":
    #SERVER_IP = "127.0.0.1"  # IP address of the UDP server
    SERVER_IP = "192.168.1.255"  # IP address of the UDP server

    SERVER_PORT = 5005       # Port of the UDP server
    send_udp_packets(SERVER_IP, SERVER_PORT)
