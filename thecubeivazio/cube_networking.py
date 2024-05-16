"""Handles everything related to networking communications"""
import traceback

import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_messages as cm

import threading
import time
import socket
from collections import deque
from typing import Deque, Tuple, Dict, Optional

from thecubeivazio.cube_messages import CubeMessage


class SendReport:
    def __init__(self, success: bool, reply_msg: Optional[CubeMessage]):
        self.success = success
        self.reply_msg = reply_msg

    @property
    def ack_msg(self):
        if self.reply_msg is not None and self.reply_msg.msgtype == cm.CubeMsgTypes.ACK:
            return cm.CubeMsgAck(copy_msg=self.reply_msg)

    def __bool__(self):
        """enables the use of SendReport as a boolean, like `if send_report:`"""
        return self.success

class CubeNetworking:
    UDP_BROADCAST_IP = "192.168.1.255"
    UDP_LISTEN_IP = "0.0.0.0"
    UDP_PORT = 5005
    UDP_BUFSIZE = 1024
    UDP_LISTEN_TIMEOUT = 0.1  # seconds

    DISCOVERY_PORT = UDP_PORT
    DISCOVERY_LOOP_TIMEOUT = 2  # seconds
    DISCOVERY_BROADCAST_IP = UDP_BROADCAST_IP
    DISCOVERY_LISTEN_IP = UDP_LISTEN_IP

    ACK_WAIT_TIMEOUT = 3  # seconds
    # TODO: set this to a ridiculously high number for production
    ACK_NB_TRIES = 1

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
        self._incoming_queue_lock = threading.Lock()

        # in order to avoid waiting multiple times by mistake for the same ack, we put the sent messages to ack in a queue
        self._ack_wait_queue = deque()
        self._ack_wait_queue_lock = threading.Lock()

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self._udp_socket.bind((self.UDP_LISTEN_IP, self.UDP_PORT))



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
        self._udp_socket.close()
        self._listenThread.join(timeout=0.1)
        self.log.info("Networking stopped")

    def get_incoming_msg_queue(self) -> Tuple[CubeMessage, ...]:
        """Returns the incoming_messages queue"""
        with self._incoming_queue_lock:
            return tuple(self.incoming_messages)

    def remove_msg_from_incoming_queue(self, message: cm.CubeMessage, force_remove=False) -> bool:
        """Removes a message from the incoming_messages queue"""
        if message.msgtype == cm.CubeMsgTypes.ACK and not force_remove:
            self.log.error("ACK messages can only be removed with force_remove=True outside of wait_for_ack_of()")
            return False
        self.log.debug(f"Removing message from listen queue: ({message.hash}) : {message}")
        with self._incoming_queue_lock:
            # noinspection PyBroadException
            try:
                self.incoming_messages.remove(message)
                # self.log.debug(f"Message removed from listen queue: ({message.hash}) : {message}")
                return True
            except:
                # self.log.error(f"Cannot remove message from listen queue ({message.hash}) :  {message}")
                return False

    def remove_msg_from_ack_wait_queue(self, message: cm.CubeMessage) -> bool:
        """Removes a message from the ack_wait_queue"""
        with self._ack_wait_queue_lock:
            # noinspection PyBroadException
            try:
                self._ack_wait_queue.remove(message)
                self.log.debug(f"Message removed from ack wait queue: ({message.hash}) : {message}")
                return True
            except:
                self.log.error(f"Failed to remove message from ack wait queue ({message.hash}) :  {message}")
                return False

    def add_msg_to_ack_wait_queue(self, message: cm.CubeMessage) -> bool:
        """Adds a message to the ack_wait_queue.
        Returns True if the message was added, False if it was already in the queue or could not be added"""
        with self._ack_wait_queue_lock:
            if message in self._ack_wait_queue:
                self.log.error(f"Already waiting for ack of message: ({message.hash}) : {message}")
                return False
            self._ack_wait_queue.append(message)
            self.log.debug(f"Message added to ack wait queue: ({message.hash}) : {message}")
            return True

    def add_msg_to_incoming_queue(self, message: cm.CubeMessage) -> bool:
        """Adds a message to the incoming_messages queue"""
        with self._incoming_queue_lock:
            self.incoming_messages.append(message)
            self.log.debug(f"Message added to incoming queue: ({message.hash}) : {message}")
            return True

    def acknowledge_this_message(self, message: cm.CubeMessage, info:cm.CubeMsgReplies=None):
        """Sends an acknowledgement message for the given message"""
        self.log.info(f"Acknowledging message: ({message.hash}) : {message}")
        ack_msg = cm.CubeMsgAck(self.node_name, message, info=info)
        ack_msg.require_ack = False
        self.send_msg_with_udp(ack_msg)
        if self.send_msg_to(ack_msg, message.sender):
            self.log.debug(f"Acknowledgement sent. Removing acked message: {ack_msg}")
            self.remove_msg_from_incoming_queue(message)
        else:
            self.log.error(f"Failed to send ack: {ack_msg}")

    def _listen_loop(self):
        """Continuously listens for incoming messages and puts them in the incoming_messages queue if they're valid.
        Do not override"""
        while self._keep_running:
            time.sleep(0.1)
            # wait for a udp message
            data, addr = self._wait_for_udp_packet()
            if not data or not addr:
                continue
            try:
                message = cm.CubeMessage()
                message.build_from_bytes(data)
            except:
                continue
            message.sender_ip = addr[0]
            if message.sender == self.node_name:
                #self.log.debug(f"Ignoring message from self : ({message.hash}) {message}")
                continue

            if not message.is_valid():
                self.log.error(f"Invalid CubeMessage. Ignoring : {data.decode()}")
                continue

            self.log.debug(f"Received valid message: {message.hash} from {addr}: {message}")

            self.add_msg_to_incoming_queue(message)
            self._handle_generic_message(message)

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
            if timeout != 0:
                self._udp_socket.settimeout(timeout)
            data, addr = self._udp_socket.recvfrom(self.UDP_BUFSIZE)
            self.log.debug(f"Received UDP packet from {addr}: {data.decode()}")
            return data, addr
        except:
            return b"", ("", 0)



    def _handle_generic_message(self, message:cm.CubeMessage) -> bool:
        # if `handled` is set to True, the message will be removed from the incoming queue
        handled = False
        self.log.debug(f"Handling message: ({message.hash}) : {message}")

        # if the sender's ip is out of date, update it
        if self.nodes_list.get_node_ip_from_node_name(message.sender) != message.sender_ip:
            self.nodes_list.set_node_ip_from_node_name(message.sender, message.sender_ip)
            self.log.info(f"Added node {message.sender} to the nodes list")
        # if it's an ack message, ignore it. It has te be handled in wait_for_ack_of()
        if message.msgtype == cm.CubeMsgTypes.ACK:
            return True
        # if it's a heartbeat, update the heartbeats list
        elif message.msgtype == cm.CubeMsgTypes.HEARTBEAT:
            self.heartbeats[message.sender] = time.time()
            handled = True
        # if it's a version request, reply with a version reply message
        elif message.msgtype == cm.CubeMsgTypes.VERSION_REQUEST:
            handled = self.send_msg_with_udp(cm.CubeMsgVersionReply(self.node_name))
        # if it's a WHO_IS message, reply with an I_AM message
        elif message.msgtype == cm.CubeMsgTypes.WHO_IS:
            target_node = message.kwargs.get("node_name_to_find")
            if target_node == self.node_name or target_node == cubeid.EVERYONE_NAME:
                handled = self.send_msg_with_udp(cm.CubeMessage(cm.CubeMsgTypes.I_AM, self.node_name))
        # if it's an I_AM message, update the nodes list with the sender's IP
        elif message.msgtype == cm.CubeMsgTypes.I_AM:
            self.nodes_list.set_node_ip_from_node_name(message.sender, self.get_self_ip())
            handled = True

        if handled:
            self.log.info(f"Handled generic message: ({message.hash}) : {message}")
            self.remove_msg_from_incoming_queue(message)
        else:
            self.log.debug(f"Not a generic message. Must be handled: ({message.hash}) : {message}")
        return handled


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
        self.log.info("Discovering cube nodes...")
        # TODO: redo with WHO_IS and I_AM messages
        return False

    # TODO: redo with WHO_IS and I_AM messages
    def discovery_response_loop(self):
        """Listens for discovery requests and responds with the node name"""
        # TODO: redo with WHO_IS and I_AM messages
        pass




    def _send_bytes_with_udp(self, data: bytes, ip: str, port: int) -> bool:
        # noinspection PyBroadException
        try:
            assert self._udp_socket.sendto(data, (ip, port)), f"Failed to send bytes to {ip}:{port}: {data.decode()}"
            self.log.debug(f"Sent bytes to {ip}:{port}: {data.decode()}")
            return True
        except Exception as e:
            self.log.error(e.__str__())
            #print(traceback.format_exc())
            return False

    def send_msg_with_udp(self, message: cm.CubeMessage, ip: str = None, port: int = None, require_ack=False, ack_timeout:int=None, nb_tries:int=None) -> SendReport:
        """Sends a message with UDP. if ack is True, waits for an acknowledgement. Returns True if the message was acknowledged, False otherwise."""
        if not message.is_valid():
            self.log.error(f"Invalid message: {message}")
            return SendReport(False, None)

        if not ip:
            ip = self.UDP_BROADCAST_IP
        if port is None:
            port = self.UDP_PORT

        if require_ack:
            message.require_ack = True
        if ack_timeout is None:
            ack_timeout = self.ACK_WAIT_TIMEOUT
        if nb_tries is None:
            nb_tries = self.ACK_NB_TRIES

        self.log.debug(f"Sending message: ({message.hash}) : {message} to {ip}:{port}")
        if not self._send_bytes_with_udp(message.to_bytes(), ip, port):
            return SendReport(False, None)

        if not message.require_ack:
            return SendReport(True, None)

        # if we require an ack, wait for it and retry if necessary
        for i in range(nb_tries):
            ack_msg = self.wait_for_ack_of(message, timeout=ack_timeout)
            if ack_msg is not None:
                return SendReport(True, ack_msg)
            self.log.error(f"Re-sending (try {i+1}/{nb_tries}) : ({message.hash}) : {message}")
            if not self._send_bytes_with_udp(message.to_bytes(), ip, port):
                return SendReport(False, None)
        self.log.error(f"Failed to get and ack for this message after {nb_tries} tries : ({message.hash}) : {message}")
        return SendReport(True, None)



    def send_msg_to(self, message: cm.CubeMessage, node_name: str, require_ack=False) -> SendReport:
        """Sends a message to a node. Returns True if the message was acknowledged, False otherwise."""
        self.log.info(f"Sending message to {node_name}: ({message.hash}) : {message}, require_ack: {require_ack}")
        ip = self.nodes_list.get_node_ip_from_node_name(node_name)
        return self.send_msg_with_udp(message, ip, require_ack=require_ack)

    def send_msg_to_all(self, message: cm.CubeMessage, require_ack=False) -> SendReport:
        """Sends a message to all nodes. Returns True if the message was acknowledged by all nodes, False otherwise."""
        self.log.info(f"Sending message to all nodes: ({message.hash}) : {message}, require_ack: {require_ack}")
        return self.send_msg_with_udp(message, self.UDP_BROADCAST_IP, require_ack=require_ack)

    def send_msg_to_cubeserver(self, message: cm.CubeMessage, require_ack=False) -> SendReport:
        """Sends a message to the CubeServer. Returns True if the message was acknowledged, False otherwise."""
        self.log.info(f"Sending message to CubeServer ({self.nodes_list.cubeServer.ip}): ({message.hash}) : {message}, require_ack: {require_ack}")
        return self.send_msg_with_udp(message, self.nodes_list.cubeServer.ip, require_ack=require_ack)

    def get_ack_wait_queue(self) -> Tuple[CubeMessage, ...]:
        """Returns the ack_wait_queue"""
        with self._ack_wait_queue_lock:
            return tuple(self._ack_wait_queue)

    # TESTME
    # TODO: redo. this will be made redundant with the new ack handling system directly in listenloop
    def wait_for_ack_of(self, msg_to_ack: cm.CubeMessage, timeout: int = None) -> Optional[cm.CubeMsgAck]:
        """Waits for an acknowledgement of a message. Returns the ack message if it was received, None otherwise.
        If timeout is None, uses the default timeout.
        If timeout is 0, wait forever."""
        self.add_msg_to_ack_wait_queue(msg_to_ack)

        if timeout is None:
            timeout = self.ACK_WAIT_TIMEOUT
        end_time = time.time() + timeout



        while self._keep_running:
            self.log.info(f"Waiting for ack of message: ({msg_to_ack.hash}) : {msg_to_ack}, timeout: {timeout} s")
            if timeout != 0 and time.time() > end_time:
                self.log.error("wait_for_ack_of timeout for : ({message.hash}) : {message}")
                return None
            for msg in self.get_incoming_msg_queue():
                # if it's an ACK message acknowledging the message we're waiting for, success
                if msg.is_ack_of(msg_to_ack):
                    self.log.info(f"Received ack of message: ({msg_to_ack.hash}) : {msg_to_ack}")
                    self.log.info(f"Removing this ack msg and our msg waiting to be acked")
                    self.remove_msg_from_incoming_queue(msg, force_remove=True)
                    self.remove_msg_from_ack_wait_queue(msg_to_ack)
                    ack_msg = cm.CubeMsgAck(copy_msg=msg)
                    return ack_msg
            time.sleep(0.1)
        return None




if __name__ == "__main__":
    # use the first argument as a node name. if blank, use CubeServer
    import sys

    if len(sys.argv) > 1:
        net = CubeNetworking(sys.argv[1])
    else:
        net = CubeNetworking(cubeid.CUBESERVER_NAME)

    net.log.info(f"Starting networking test for {net.node_name}")
    net.run()
