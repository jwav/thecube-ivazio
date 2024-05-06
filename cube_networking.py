"""Handles everything related to networking communications"""
import cube_identification as cubeid
import cube_logger as cube_logger

import threading
import time


import socket




class CubeNetworking:
    DISCOVERY_PORT = 5005
    DISCOVERY_LOOP_TIMEOUT = 2  # seconds
    DISCOVERY_BROADCAST_IP = "192.168.1.255"
    DISCOVERY_LISTEN_IP = "0.0.0.0"
    DISCOVERY_BUFSIZE = 1024

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.log = cube_logger.make_logger(f"{node_name} Networking")
        self._thread = None
        self._keep_running = False

        self.nodes_list = cubeid.NodesList()
        self.nodes_list.set_node_ip_from_node_name(self.node_name, self.get_self_ip())

        # check if the node name is valid. If not, raise an exception
        if not cubeid.is_valid_node_name(node_name):
            self.log.error(f"Invalid node name: {node_name}")
            raise ValueError(f"Invalid node name: {node_name}")

    def start(self):
        """launches a thread running _main_loop"""
        self._thread = threading.Thread(target=self._main_loop)
        self._keep_running = True
        self._thread.start()

    def stop(self):
        """stops the main loop thread"""
        self._thread.join()

    # TODO
    def _main_loop(self):
        """Main loop of the networking thread. To be overridden by subclasses."""
        while self._keep_running:
            self.log.debug("Dummy main loop iteration")
            time.sleep(1)

    @staticmethod
    def get_self_ip():
        """Returns the IP of the current node"""
        return socket.gethostbyname(socket.gethostname())

    def discovery_loop(self):
        """Main loop of the discovery thread"""
        while self._keep_running and not self.nodes_list.is_complete():
            self.discover_servers()
            time.sleep(1)

    def discover_servers(self, timeout=None) -> bool:
        if timeout is None:
            timeout = self.DISCOVERY_LOOP_TIMEOUT
        self.log.info("Discovering servers...")
        message = cubeid.IDENTIFICATION_MESSAGE.encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(message, (self.DISCOVERY_BROADCAST_IP, self.DISCOVERY_PORT))
            while True:
                try:
                    sock.settimeout(timeout)
                    data, addr = sock.recvfrom(self.DISCOVERY_BUFSIZE)
                    self.log.debug(f"Received response from {addr}: {data.decode()}")
                    name = cubeid.get_node_name_from_response(data.decode())
                    if name == cubeid.FRONTDESK_NAME:
                        self.nodes_list.frontDesk.ip = addr[0]
                        self.log.info(f"found FrontDesk IP: {self.nodes_list.frontDesk.ip}")
                        return True
                    elif name == cubeid.CUBESERVER_NAME:
                        self.nodes_list.cubeServer.ip = addr[0]
                        self.log.info(f"found CubeServer IP: {self.nodes_list.cubeServer.ip}")
                        return True
                    elif name.startswith(cubeid.CUBEBOX_NAME_PREFIX):
                        for cubebox in self.nodes_list.cubeBoxes:
                            if name == cubebox.name:
                                cubebox.ip = addr[0]
                                self.log.info(f"found CubeBox IP: {cubebox.ip}")
                                return True
                    else:
                        self.log.debug("Unknown response")
                        return False
                except socket.timeout:
                    self.log.info("Discovery timeout")
                    return False

    def discovery_response_loop(self):
        """Listens for discovery requests and responds with the node name"""
        self.log.info("Starting discovery response loop")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.DISCOVERY_LISTEN_IP, self.DISCOVERY_PORT))
            while True:
                data, addr = sock.recvfrom(self.DISCOVERY_BUFSIZE)
                self.log.debug(f"Received message: {data.decode()} from {addr}")
                if data.decode() == cubeid.IDENTIFICATION_MESSAGE:
                    response = cubeid.make_response_from_node_name(self.node_name).encode()
                    sock.sendto(response, addr)
                    self.log.info(f"Sent response to {addr}: {response.decode()}")
                    self.nodes_list.cubeServer.ip = addr[0]
                    break


if __name__ == "__main__":
    # use the first argument as a node name. if blank, use CubeServer
    import sys

    if len(sys.argv) > 1:
        net = CubeNetworking(sys.argv[1])
    else:
        net = CubeNetworking(cubeid.CUBESERVER_NAME)

    print("self ip:", net.get_self_ip())
    while True:
        net.discover_servers()
        if net.nodes_list.is_complete():
            break
    print(net.nodes_list.to_string())
