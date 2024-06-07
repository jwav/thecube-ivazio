"""Handles everything related to networking communications"""
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_messages as cm
from thecubeivazio.cube_common_defines import *

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

    @property
    def ack_info(self) -> Optional[cm.CubeAckInfos]:
        # noinspection PyBroadException
        try:
            return self.ack_msg.info
        except:
            return None

    @property
    def ok(self):
        # noinspection PyBroadException
        try:
            return self.ack_info == cm.CubeAckInfos.OK
        except:
            return False

    def __bool__(self):
        """enables the use of SendReport as a boolean, like `if send_report:`"""
        return self.success


class CubeNetworking:
    UDP_BROADCAST_IP = "192.168.1.255"
    UDP_LISTEN_IP = "0.0.0.0"
    UDP_PORT = 5005
    UDP_BUFSIZE = 9001 # let's set it over 9000 to be safe
    UDP_LISTEN_TIMEOUT = 0.1  # seconds

    DISCOVERY_PORT = UDP_PORT
    DISCOVERY_LOOP_TIMEOUT = 2  # seconds
    DISCOVERY_BROADCAST_IP = UDP_BROADCAST_IP
    DISCOVERY_LISTEN_IP = UDP_LISTEN_IP

    ACK_WAIT_TIMEOUT = 2  # seconds
    # TODO: set this to a ridiculously high number for production
    ACK_NB_TRIES = 3

    def __init__(self, node_name: str, log_filename: str = None):
        self.log = cube_logger.CubeLogger(name=f"{node_name} Networking", log_filename=log_filename)

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

        # sometimes, a sent message will not be acknowledged. Let's put these messages in a queue and retry sending them some time later
        self._retry_queue = deque()
        self._retry_queue_lock = threading.Lock()

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcasting
        self._udp_socket.bind((self.UDP_LISTEN_IP, self.UDP_PORT))

        self.nodes_list = cubeid.NodesList()
        # add own IP to the nodes list
        self.nodes_list.set_node_ip_for_node_name(self.node_name, self.get_self_ip())

        self.incoming_messages: Deque[cm.CubeMessage] = deque()

        self.heartbeats: Dict[str, float] = {}

    def run(self):
        """launches the listening and sending threads.
        DO OVERRIDE THIS after calling super()"""
        self._listenThread = threading.Thread(target=self._listen_loop)
        # make the thread a daemon so it stops when the main thread stops
        self._listenThread.daemon = True
        self._keep_running = True
        self._listenThread.start()

    def is_running(self):
        """Returns True if the networking is running, False otherwise"""
        return self._keep_running

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
        self.log.debug(f"Removing message from listen queue: ({message.hash})")
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
                self.log.debug(f"Message removed from ack wait queue: ({message.hash})")
                return True
            except:
                self.log.error(f"Failed to remove message from ack wait queue ({message.hash})")
                return False

    def add_msg_to_ack_wait_queue(self, message: cm.CubeMessage) -> bool:
        """Adds a message to the ack_wait_queue.
        Returns True if the message was added, False if it was already in the queue or could not be added"""
        with self._ack_wait_queue_lock:
            if message in self._ack_wait_queue:
                self.log.warning(f"Already waiting for ack of message: ({message.hash})")
                return False
            self._ack_wait_queue.append(message)
            self.log.debug(f"Message added to ack wait queue: ({message.hash}) : {message}")
            return True

    def add_msg_to_retry_queue(self, message: cm.CubeMessage) -> bool:
        """Adds a message to the retry_queue"""
        with self._retry_queue_lock:
            if message in self._retry_queue:
                self.log.warning(f"Already waiting to retry message: ({message.hash})")
                return False
            self._retry_queue.append(message)
            self.log.debug(f"Message added to retry queue: ({message.hash})")
            return True

    def remove_msg_from_retry_queue(self, message: cm.CubeMessage) -> bool:
        """Removes a message from the retry_queue"""
        with self._retry_queue_lock:
            # noinspection PyBroadException
            try:
                self._retry_queue.remove(message)
                self.log.debug(f"Message removed from retry queue: ({message.hash})")
                return True
            except:
                self.log.error(f"Failed to remove message from retry queue ({message.hash})")
                return False

    def add_msg_to_incoming_queue(self, message: cm.CubeMessage) -> bool:
        """Adds a message to the incoming_messages queue"""
        with self._incoming_queue_lock:
            self.incoming_messages.append(message)
            self.log.debug(f"Message added to incoming queue: ({message.hash}) : {message}")
            return True

    def acknowledge_this_message(self, message: cm.CubeMessage, info: cm.CubeAckInfos = None):
        """Sends an acknowledgement message for the given message"""
        self.log.debug(f"Acknowledging message: ({message.hash})")
        ack_msg = cm.CubeMsgAck(self.node_name, message, info=info)
        ack_msg.require_ack = False
        self.send_msg_with_udp(ack_msg)
        if self.send_msg_to(ack_msg, message.sender):
            self.log.infoplus(f"Acknowledgement sent. Removing acked message: ({ack_msg.hash})")
            self.remove_msg_from_incoming_queue(message)
        else:
            self.log.error(f"Failed to send ack: ({ack_msg.hash})")

    def _listen_loop(self):
        """Continuously listens for incoming messages and puts them in the incoming_messages queue if they're valid.
        Do not override"""
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
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
                # self.log.debug(f"Ignoring message from self : ({message.hash}) {message}")
                continue

            if not message.is_valid():
                self.log.error(f"Invalid CubeMessage. Ignoring : {data.decode()}")
                continue

            self.log.debug(f"Received valid message from {message.sender} : ({message.hash}) {message}")

            self.add_msg_to_incoming_queue(message)
            self._remove_useless_ack_messages()
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
            self.log.debug(f"Received UDP packet from {addr}: {len(data)} bytes")
            return data, addr
        except:
            return b"", ("", 0)

    def _remove_useless_ack_messages(self):
        """Removes ack messages from the incoming queue which do not match any message in the ack_wait_queue"""
        messages = self.get_incoming_msg_queue()
        for msg in messages:
            if msg.msgtype == cm.CubeMsgTypes.ACK:
                for msg_to_be_acked in self.get_ack_wait_queue():
                    if msg.is_ack_of(msg_to_be_acked):
                        break
                else:
                    # self.log.warning(f"Removing useless ack message: ({msg.hash})")
                    self.remove_msg_from_incoming_queue(msg, force_remove=True)

    def _handle_generic_message(self, message: cm.CubeMessage) -> bool:
        """Handles messages in a manner common to all nodes.
        Returns True if the message was handled, False otherwise.
        If the message was sent by self.node_name, ignore and return True."""
        if message.sender == self.node_name:
            # self.log.debug(f"Ignoring message from self : ({message.hash}) {message}")
            return True
        # if `handled` is set to True, the message will be removed from the incoming queue
        handled = False
        self.log.debug(f"Handling message: ({message.hash}) : {message}")

        # if the sender's ip is out of date, update it
        if self.nodes_list.get_node_ip_from_node_name(message.sender) != message.sender_ip:
            self.nodes_list.set_node_ip_for_node_name(message.sender, message.sender_ip)
            self.log.info(f"Added node {message.sender} to the nodes list")
        # update the last message timestamp of the sender
        self.nodes_list.set_last_msg_timestamp_for_node_name(message.sender, time.time())
        # if it's an ack message, ignore it. It has te be handled in wait_for_ack_of()
        if message.msgtype == cm.CubeMsgTypes.ACK:
            return True
        # if it's a heartbeat, update the heartbeats list
        elif message.msgtype == cm.CubeMsgTypes.HEARTBEAT:
            self.heartbeats[message.sender] = time.time()
            handled = True
        # if it's a version request, reply with a version reply message
        elif message.msgtype == cm.CubeMsgTypes.REQUEST_VISION:
            handled = self.send_msg_with_udp(cm.CubeMsgReplyVersion(self.node_name))
        # if it's a WHO_IS message, acknowledge it
        elif message.msgtype == cm.CubeMsgTypes.WHO_IS:
            wi_msg = cm.CubeMsgWhoIs(copy_msg=message)
            if wi_msg.node_name_to_find in (self.node_name, cubeid.EVERYONE_NODENAME) \
                    and wi_msg.sender != self.node_name:
                self.log.info(f"acknowledging WHO_IS message")
                self.acknowledge_this_message(message)
            handled = True
        if handled:
            self.log.info(f"Handled generic message: ({message.hash}) : {message}")
            self.remove_msg_from_incoming_queue(message)
        else:
            self.log.debug(f"Not a generic message. Must be handled: ({message.hash})")
        return handled

    @staticmethod
    def get_self_ip():
        """Returns the IP of the current node"""
        return socket.gethostbyname(socket.gethostname())

    # NOTE: we'll just be broadcasting now. there are problems when sending to a specific ip
    @cubetry
    def _send_bytes_with_udp(self, data: bytes, ip: str, port: int) -> bool:
        """NOTE: we'll just be broadcasting now. there are problems when sending to a specific ip
        Sends bytes with UDP. Returns True if the bytes were sent, False otherwise."""
        # noinspection PyBroadException
        ip = self.UDP_BROADCAST_IP
        assert self._udp_socket.sendto(data, (ip, port)), f"Failed to send bytes to {ip}:{port}: {data.decode()}"
        self.log.debug(f"Sent bytes to {ip}:{port}: {data.decode()}")
        return True

    def send_msg_with_udp(self, message: cm.CubeMessage, ip: str = None, port: int = None, require_ack:bool=None,
                          ack_timeout: int = None, nb_tries: int = None) -> SendReport:
        """Sends a message with UDP.
        If require_ack is None, uses the message's require_ack attribute.
        Returns True if the message was acknowledged, False otherwise."""
        if not message.is_valid():
            self.log.error(f"Invalid message: {message}")
            return SendReport(False, None)

        if not ip:
            ip = self.UDP_BROADCAST_IP
        if port is None:
            port = self.UDP_PORT

        # if require_ack is None, use the message's require_ack attribute
        if require_ack is None:
            require_ack = message.require_ack
        else:
            message.require_ack = require_ack
        # if ack_timeout is None, use the default value
        if ack_timeout is None:
            ack_timeout = self.ACK_WAIT_TIMEOUT
        # if nb_tries is None, use the default value
        if nb_tries is None:
            nb_tries = self.ACK_NB_TRIES

        self.log.debug(f"Sending message to {ip}:{port} ({message.hash}) : {message} ")
        if not self._send_bytes_with_udp(message.to_bytes(), ip, port):
            return SendReport(False, None)

        if not message.require_ack:
            return SendReport(True, None)

        # if we require an ack, wait for it and retry if necessary
        for i in range(nb_tries):
            ack_msg = self.wait_for_ack_of(message, timeout=ack_timeout)
            if ack_msg is not None:
                return SendReport(True, ack_msg)
            self.log.warning(f"Re-sending (try {i + 1}/{nb_tries}) : ({message.hash})")
            if not self._send_bytes_with_udp(message.to_bytes(), ip, port):
                return SendReport(False, None)
        self.log.error(f"Failed to get an ack for this message after {nb_tries} tries : ({message.hash})")
        self.add_msg_to_retry_queue(message)
        return SendReport(True, None)

    def send_msg_to(self, message: cm.CubeMessage, node_name: str, require_ack=False, nb_tries=None) -> SendReport:
        """Sends a message to a node. Returns True if the message was acknowledged, False otherwise."""
        self.log.info(f"Sending message to {node_name}: ({message.hash}), require_ack: {require_ack}\n{message}")
        ip = self.nodes_list.get_node_ip_from_node_name(node_name)
        return self.send_msg_with_udp(message, ip, require_ack=require_ack, nb_tries=nb_tries)

    def send_msg_to_all(self, message: cm.CubeMessage, require_ack=False, nb_tries=None) -> SendReport:
        """Sends a message to all nodes. Returns True if the message was acknowledged by all nodes, False otherwise."""
        self.log.info(f"Sending message to all nodes: ({message.hash}), require_ack: {require_ack}\n{message}")
        return self.send_msg_with_udp(message, self.UDP_BROADCAST_IP, require_ack=require_ack, nb_tries=nb_tries)

    def send_msg_to_cubemaster(self, message: cm.CubeMessage, require_ack=False, nb_tries=None) -> SendReport:
        """Sends a message to the CubeMaster. Returns True if the message was acknowledged, False otherwise."""
        self.log.info(
            f"Sending message to CubeMaster ({self.nodes_list.cubemaster.ip}): ({message.hash}), require_ack: {require_ack}\n{message}")
        return self.send_msg_with_udp(message, self.nodes_list.cubemaster.ip, require_ack=require_ack, nb_tries=nb_tries)

    def send_msg_to_frontdesk(self, message: cm.CubeMessage, require_ack=False, nb_tries=None) -> SendReport:
        """Sends a message to the FrontDesk. Returns True if the message was acknowledged, False otherwise."""
        self.log.info(
            f"Sending message to FrontDesk ({self.nodes_list.frontdesk.ip}): ({message.hash}), require_ack: {require_ack}\n{message}")
        return self.send_msg_with_udp(message, self.nodes_list.frontdesk.ip, require_ack=require_ack, nb_tries=nb_tries)

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

        self.log.info(f"Waiting for ack of message: ({msg_to_ack.hash}), timeout: {timeout} s ...")
        while self._keep_running:
            # print(",", end="")
            if timeout != 0 and time.time() > end_time:
                self.log.error(f"wait_for_ack_of timeout for : ({msg_to_ack.hash})")
                return None
            for msg in self.get_incoming_msg_queue():
                # print("/", end="")
                # if it's an ACK message acknowledging the message we're waiting for, success
                if msg.is_ack_of(msg_to_ack):
                    self.log.info(f"Received ack of message: ({msg_to_ack.hash})")
                    self.log.info(f"Removing this ack msg and our msg waiting to be acked")
                    self.remove_msg_from_incoming_queue(msg, force_remove=True)
                    self.remove_msg_from_ack_wait_queue(msg_to_ack)
                    ack_msg = cm.CubeMsgAck(copy_msg=msg)
                    return ack_msg
            time.sleep(LOOP_PERIOD_SEC)
        return None

    def wait_for_message(self, msgtype: cm.CubeMsgTypes, timeout: int = None) -> Optional[CubeMessage]:
        """Waits for a message of a specific type. Returns the message if it was received, None otherwise.
        If timeout is None, uses the default timeout.
        If timeout is 0, wait forever."""
        if timeout is None:
            timeout = self.ACK_WAIT_TIMEOUT
        end_time = time.time() + timeout

        self.log.info(f"Waiting for message of type {msgtype} ...")
        while self._keep_running:
            if timeout != 0 and time.time() > end_time:
                self.log.error(f"wait_for_message timeout for message of type {msgtype}")
                return None
            for msg in self.get_incoming_msg_queue():
                if msg.msgtype == msgtype:
                    self.log.info(f"Received message of type {msgtype} : ({msg.hash})")
                    self.remove_msg_from_incoming_queue(msg)
                    return msg
            time.sleep(LOOP_PERIOD_SEC)
        return None


if __name__ == "__main__":
    # use the first argument as a node name. if blank, use CubeMaster
    import sys

    if len(sys.argv) > 1:
        net = CubeNetworking(sys.argv[1])
    else:
        net = CubeNetworking(cubeid.CUBEMASTER_NODENAME)

    net.log.info(f"Starting networking test for {net.node_name}")
    net.run()
