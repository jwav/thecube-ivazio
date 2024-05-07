"""Handles everything related to networking communications"""

import cube_identification as cubeid
import cube_logger as cube_logger
import cube_messages as cm

import threading
import time
import socket
from collections import deque
from typing import Deque


# TODO : make two threads : one for listening and one for sending
#  let's just do UDP for now, the whole discovery thing is a pain

class CubeNetworking:
    UDP_BROADCAST_IP = "192.168.1.255"
    UDP_LISTEN_IP = "0.0.0.0"
    UDP_PORT = 5005
    UDP_BUFSIZE = 1024

    DISCOVERY_PORT = UDP_PORT
    DISCOVERY_LOOP_TIMEOUT = 2  # seconds
    DISCOVERY_BROADCAST_IP = UDP_BROADCAST_IP
    DISCOVERY_LISTEN_IP = UDP_LISTEN_IP

    ACK_WAIT_TIMEOUT = 2  # seconds
    # TODO: set this to a ridiculously high number for production
    ACK_NB_TRIES = 2

    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(f"{node_name} Networking")

        # check if the node name is valid. If not, raise an exception
        if not cubeid.is_valid_node_name(node_name):
            self.log.error(f"Invalid node name: {node_name}")
            raise ValueError(f"Invalid node name: {node_name}")

        self.node_name = node_name
        self._listenThread = None
        self._keep_running = False
        self._listenLock = threading.Lock()

        self.nodes_list = cubeid.NodesList()
        # add own IP to the nodes list
        self.nodes_list.set_node_ip_from_node_name(self.node_name, self.get_self_ip())

        self.incoming_messages: Deque[cm.CubeMessage] = deque()

    def run(self):
        """launches the listening and sending threads.
        DO OVERRIDE THIS after calling super()"""
        self._listenThread = threading.Thread(target=self._listen_loop)
        self._keep_running = True
        self._listenThread.start()

    def stop(self):
        """stops the main loop thread"""
        self._keep_running = False
        self._listenThread.join()

    def get_incoming_msg_queue(self) -> Deque[cm.CubeMessage]:
        """Returns the incoming_messages queue"""
        with self._listenLock:
            return self.incoming_messages

    def remove_from_incoming_msg_queue(self, message: cm.CubeMessage):
        """Removes a message from the incoming_messages queue"""
        with self._listenLock:
            self.incoming_messages.remove(message)

    def acknowledge_message(self, message: cm.CubeMessage):
        """Sends an acknowledgement message for the given message"""
        ack_msg = message.copy()
        ack_msg.msgtype = cm.CubeMsgType.ACK
        ack_msg.require_ack = False
        self.send_msg_with_udp(ack_msg)

    def _listen_loop(self):
        """Continuously listens for incoming messages and puts them in the incoming_messages queue if they're valid.
        Do not override"""
        while self._keep_running:
            # wait for a udp message
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind((self.UDP_LISTEN_IP, self.UDP_PORT))
                data, addr = sock.recvfrom(1024)
                self.log.debug(f"Received message: {data.decode()} from {addr}")
                message = cm.CubeMessage.make_from_bytes(data)
                if message.sender == self.node_name:
                    self.log.debug("Ignoring message from self")
                    continue
                if message.is_valid():
                    with self._listenLock:
                        self.incoming_messages.append(message)
                    self.log.info(f"Valid message: {message}")
                else:
                    self.log.error(f"Invalid message: {data.decode()}")
            self._handle_common_incoming_messages()
            time.sleep(0.1)

    def _handle_common_incoming_messages(self):
        """Handles common incoming messages. Do not override."""
        messages = self.get_incoming_msg_queue()
        for message in messages:
            # if the sender is not known, add it to the nodes list
            if not self.nodes_list.get_node_ip_from_node_name(message.sender):
                self.nodes_list.set_node_ip_from_node_name(message.sender, self.get_self_ip())
                self.log.info(f"Added node {message.sender} to the nodes list")

            result = False
            if message.msgtype == cm.CubeMsgType.VERSION_REQUEST:
                result = self.send_msg_with_udp(cm.CubeMsgVersionReply(self.node_name))
            elif message.msgtype == cm.CubeMsgType.WHO_IS:
                if message.kwargs.get("node_name_to_find") == self.node_name:
                    result = self.send_msg_with_udp(cm.CubeMessage(cm.CubeMsgType.I_AM, self.node_name))
            elif message.msgtype == cm.CubeMsgType.I_AM:
                self.nodes_list.set_node_ip_from_node_name(message.sender, self.get_self_ip())
                result = True

            if result:
                self.log.info(f"Handled message: {message}")
                self.remove_from_incoming_msg_queue(message)


    @staticmethod
    def get_self_ip():
        """Returns the IP of the current node"""
        return socket.gethostbyname(socket.gethostname())

    # TODO: redo with WHO_IS and I_AM messages
    def discovery_loop(self):
        """Main loop of the discovery thread"""
        while self._keep_running and not self.nodes_list.is_complete():
            self.discover_servers()
            time.sleep(1)

    # TODO: redo with WHO_IS and I_AM messages
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
                    data, addr = sock.recvfrom(self.UDP_BUFSIZE)
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

    # TODO: redo with WHO_IS and I_AM messages
    def discovery_response_loop(self):
        """Listens for discovery requests and responds with the node name"""
        self.log.info("Starting discovery response loop")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.DISCOVERY_LISTEN_IP, self.DISCOVERY_PORT))
            while True:
                data, addr = sock.recvfrom(self.UDP_BUFSIZE)
                self.log.debug(f"Received message: {data.decode()} from {addr}")
                if data.decode() == cubeid.IDENTIFICATION_MESSAGE:
                    response = cubeid.make_response_from_node_name(self.node_name).encode()
                    sock.sendto(response, addr)
                    self.log.info(f"Sent response to {addr}: {response.decode()}")
                    self.nodes_list.cubeServer.ip = addr[0]
                    break

    # TESTME
    def send_msg_with_udp(self, message: cm.CubeMessage, ip: str = None, port: int = None, require_ack=False) -> bool:
        """Sends a message with UDP. if ack is True, waits for an acknowledgement. Returns True if the message was acknowledged, False otherwise."""
        if not message.is_valid():
            self.log.error(f"Invalid message: {message}")
            return False

        if not ip:
            ip = self.UDP_BROADCAST_IP
        if port is None:
            port = self.UDP_PORT

        self.log.debug(f"Sending message: {message} to {ip}:{port}")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast
            sock.sendto(message.to_bytes(), (ip, port))

        if require_ack or message.require_ack:
            for i in range(self.ACK_NB_TRIES):
                self.log.debug(f"Waiting for ack of message: {message}")
                if self.wait_for_ack(message):
                    return True
            self.log.error(f"Message not acknowledged after {self.ACK_NB_TRIES} tries")
            return False
        else:
            self.log.debug("Not waiting for ack")
            return True

    def send_msg_to(self, message: cm.CubeMessage, node_name: str, require_ack=True) -> bool:
        """Sends a message to a node. Returns True if the message was acknowledged, False otherwise."""
        ip = self.nodes_list.get_node_ip_from_node_name(node_name)
        return self.send_msg_with_udp(message, ip, require_ack=require_ack)

    def send_msg_to_cubeserver(self, message: cm.CubeMessage, require_ack=True) -> bool:
        """Sends a message to the CubeServer. Returns True if the message was acknowledged, False otherwise."""
        return self.send_msg_with_udp(message, self.nodes_list.cubeServer.ip, require_ack=require_ack)

    # TESTME
    def wait_for_ack(self, message: cm.CubeMessage, timeout: int = None) -> bool:
        """Waits for an acknowledgement of a message. Returns True if the message was acknowledged, False otherwise.
        If timeout is None, uses the default timeout.
        If timeout is 0, wait forever."""
        if timeout is None:
            timeout = self.ACK_WAIT_TIMEOUT
        end_time = time.time() + timeout

        self.log.debug(f"Waiting for ack of message: {message}, timeout: {timeout} s")

        while True:
            if timeout != 0 and time.time() > end_time:
                self.log.debug("Ack timeout")
                return False
            with self._listenLock:
                for msg in self.incoming_messages:
                    if msg.is_ack_of(message):
                        self.log.info(f"Received ack: {msg}")
                        return True
            time.sleep(0.1)


if __name__ == "__main__":
    # use the first argument as a node name. if blank, use CubeServer
    import sys

    if len(sys.argv) > 1:
        net = CubeNetworking(sys.argv[1])
    else:
        net = CubeNetworking(cubeid.CUBESERVER_NAME)

    net.log.info(f"Starting networking test for {net.node_name}")
    net.run()
