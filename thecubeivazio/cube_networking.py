"""Handles everything related to networking communications"""

import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_messages as cm

import threading
import time
import socket
from collections import deque
from typing import Deque, Tuple, Dict

from thecubeivazio.cube_messages import CubeMessage


# TODO: are messages well acknowledged? I dont remember right now
# TODO: apparently not. we get an inifinite loop of acks


class CubeNetworking:
    UDP_BROADCAST_IP = "192.168.1.255"
    UDP_LISTEN_IP = "0.0.0.0"
    UDP_PORT = 5005
    UDP_BUFSIZE = 1024
    UDP_LISTEN_TIMEOUT = 0  # seconds

    DISCOVERY_PORT = UDP_PORT
    DISCOVERY_LOOP_TIMEOUT = 2  # seconds
    DISCOVERY_BROADCAST_IP = UDP_BROADCAST_IP
    DISCOVERY_LISTEN_IP = UDP_LISTEN_IP

    ACK_WAIT_TIMEOUT = 2  # seconds
    # TODO: set this to a ridiculously high number for production
    ACK_NB_TRIES = 2

    def __init__(self, node_name: str, log_filename:str=None):
        self.log = cube_logger.make_logger(name=f"{node_name} Networking", log_filename=log_filename)

        # check if the node name is valid. If not, raise an exception
        if not cubeid.is_valid_node_name(node_name):
            self.log.error(f"Invalid node name: {node_name}")
            raise ValueError(f"Invalid node name: {node_name}")

        # params declaration
        self.node_name = node_name
        self._listenThread = None
        self._keep_running = False
        self._listenLock = threading.Lock()

        self.nodes_list = cubeid.NodesList()
        # add own IP to the nodes list
        self.nodes_list.set_node_ip_from_node_name(self.node_name, self.get_self_ip())

        self.incoming_messages: Deque[cm.CubeMessage] = deque()

        self.heartbeats : Dict[str,float] = {}

    def run(self):
        """launches the listening and sending threads.
        DO OVERRIDE THIS after calling super()"""
        self._listenThread = threading.Thread(target=self._listen_loop)
        self._keep_running = True
        self._listenThread.start()

    def stop(self):
        """stops the main loop thread"""
        self.log.info("Stopping networking...")
        self._keep_running = False
        self._listenThread.join(timeout=1)
        self.log.info("Networking stopped")

    def get_incoming_msg_queue(self) -> Tuple[CubeMessage, ...]:
        """Returns the incoming_messages queue"""
        with self._listenLock:
            return tuple(self.incoming_messages)

    def remove_from_incoming_msg_queue(self, message: cm.CubeMessage) -> bool:
        """Removes a message from the incoming_messages queue"""
        self.log.debug(f"Removing message from listen queue: ({message.hash}) : {message}")
        with self._listenLock:
            # noinspection PyBroadException
            try:
                self.incoming_messages.remove(message)
                self.log.debug(f"Message removed from listen queue: ({message.hash}) : {message}")
                return True
            except:
                self.log.error(f"Cannot remove message from listen queue ({message.hash}) :  {message}")
                return False

    def acknowledge_message(self, message: cm.CubeMessage):
        """Sends an acknowledgement message for the given message"""
        self.log.info(f"Acknowledging message: ({message.hash}) : {message}")
        # TODO : use hash and special instance instead of copying message
        ack_msg = cm.CubeMsgAck(self.node_name, message)
        ack_msg.require_ack = False
        self.send_msg_with_udp(ack_msg)
        if self.send_msg_to(ack_msg, message.sender):
            self.log.debug(f"Acknowledgement sent: {ack_msg}")
            self.remove_from_incoming_msg_queue(message)
        else:
            self.log.error(f"Failed to send ack: {ack_msg}")

    def _listen_loop(self):
        """Continuously listens for incoming messages and puts them in the incoming_messages queue if they're valid.
        Do not override"""
        while self._keep_running:
            # wait for a udp message
            data, addr = self._wait_for_udp_packet()
            if not data or not addr:
                continue
            message = cm.CubeMessage.make_from_bytes(data)
            self.log.debug(f"Received message: {message.hash} from {addr}: {message}")
            message = cm.CubeMessage.make_from_bytes(data)
            message.sender_ip = addr[0]
            if message.sender == self.node_name:
                self.log.debug(f"Ignoring message from self : ({message.hash}) {message}")
                continue
            if message.is_valid():
                with self._listenLock:
                    self.incoming_messages.append(message)
                self.log.info(f"Valid message: {message}")
            else:
                self.log.error(f"Invalid message: {data.decode()}")
            self._handle_common_incoming_messages()
            time.sleep(0.1)
            print(",", end="")

    def _wait_for_udp_packet(self, ip=None, port=None, timeout=None) -> Tuple[bytes, Tuple[str, int]]:
        """Receives a UDP packet. Returns the data and the address of the sender.
        If ip is None, uses the default listen IP.
        If port is None, uses the default port.
        If timeout is None, uses the default timeout.
        If timeout is 0, waits forever."""
        if ip is None:
            ip = self.UDP_LISTEN_IP
        if port is None:
            port = self.UDP_PORT
        if timeout is None:
            timeout = self.UDP_LISTEN_TIMEOUT
        # noinspection PyBroadException
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                self.log.debug(f"Getting UDP packet from ip={ip}, port={port}, timeout={timeout}")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # Allow multiple instances to use the same port
                sock.bind((ip, port))
                if timeout != 0:
                    sock.settimeout(timeout)
                data, addr = sock.recvfrom(self.UDP_BUFSIZE)
                self.log.debug(f"Received UDP packet from {addr}: {data.decode()}")
                return data, addr
        except:
            return b"", ("", 0)

    def _handle_common_incoming_messages(self):
        """Handles common incoming messages. Do not override."""
        self.log.debug("Handling common incoming messages")
        messages = self.get_incoming_msg_queue()
        for message in messages:
            result = False

            self.log.debug(f"Handling message: ({message.hash}) : {message}")
            # if the sender is not known, add it to the nodes list
            if not self.nodes_list.get_node_ip_from_node_name(message.sender) and message.sender_ip:
                self.nodes_list.set_node_ip_from_node_name(message.sender, message.sender_ip)
                self.log.info(f"Added node {message.sender} to the nodes list")

            if message.msgtype == cm.CubeMsgType.HEARTBEAT:
                self.heartbeats[message.sender] = time.time()
                result = True

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
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # Allow multiple instances to use the same port
            sock.sendto(message, (self.DISCOVERY_BROADCAST_IP, self.DISCOVERY_PORT))
            while self._keep_running and time.time() < time.time() + timeout:
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
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # Allow multiple instances to use the same port
            sock.bind((self.DISCOVERY_LISTEN_IP, self.DISCOVERY_PORT))
            while self._keep_running:
                data, addr = sock.recvfrom(self.UDP_BUFSIZE)
                message = cm.CubeMessage.make_from_bytes(data)
                self.log.debug(f"Discovery response : Received message: ({message.hash}) from {addr} : {data.decode()}")
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

        self.log.debug(f"Sending message: ({message.hash}) : {message} to {ip}:{port}")
        self._send_bytes_with_udp(message.to_bytes(), ip, port)

        self.log.debug(f"msg require ack? {message.require_ack}, require_ack? {require_ack}")
        if require_ack or message.require_ack:
            for i in range(self.ACK_NB_TRIES):
                self.log.debug(f"Waiting for ack of message: ({message.hash}) : {message} (nb try: {i}/{self.ACK_NB_TRIES})")
                if self.wait_for_ack(message):
                    return True
                else:
                    self.log.error(f"Message not acknowledged after {i} tries. Re-sending ({message.hash}).")
                    self._send_bytes_with_udp(message.to_bytes(), ip, port)
            return False
        else:
            self.log.debug("Not waiting for ack")
            return True

    def _send_bytes_with_udp(self, data: bytes, ip: str, port: int):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)  # Allow multiple instances to use the same port
            sock.bind((ip, port))
            sock.sendto(data, (ip, port))
            self.log.debug(f"Sent bytes to {ip}:{port}: {data.decode()}")

    def send_msg_to(self, message: cm.CubeMessage, node_name: str, require_ack=False) -> bool:
        """Sends a message to a node. Returns True if the message was acknowledged, False otherwise."""
        self.log.debug(f"Sending message to {node_name}: ({message.hash}) : {message}, require_ack: {require_ack}")
        ip = self.nodes_list.get_node_ip_from_node_name(node_name)
        return self.send_msg_with_udp(message, ip, require_ack=require_ack)

    def send_msg_to_cubeserver(self, message: cm.CubeMessage, require_ack=False) -> bool:
        """Sends a message to the CubeServer. Returns True if the message was acknowledged, False otherwise."""
        self.log.debug(f"Sending message to CubeServer ({self.nodes_list.cubeServer.ip}): ({message.hash}) : {message}, require_ack: {require_ack}")
        return self.send_msg_with_udp(message, self.nodes_list.cubeServer.ip, require_ack=require_ack)

    # TESTME
    def wait_for_ack(self, message: cm.CubeMessage, timeout: int = None) -> bool:
        """Waits for an acknowledgement of a message. Returns True if the message was acknowledged, False otherwise.
        If timeout is None, uses the default timeout.
        If timeout is 0, wait forever."""
        if timeout is None:
            timeout = self.ACK_WAIT_TIMEOUT
        end_time = time.time() + timeout

        self.log.debug(f"Waiting for ack of message: ({message.hash}) : {message}, timeout: {timeout} s")

        while self._keep_running:
            if timeout != 0 and time.time() > end_time:
                self.log.debug("Ack timeout")
                return False
            for msg in self.get_incoming_msg_queue():
                if msg.is_ack_of(message):
                    self.log.info(f"Received ack msg: ({msg.hash}) : {msg}")
                    self.remove_from_incoming_msg_queue(msg)
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
