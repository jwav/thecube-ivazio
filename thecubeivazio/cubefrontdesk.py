"""The backend of the cube front desk system. Meant to be implemented by cubegui"""

import threading
import time

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game

class CubeFrontDesk:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.make_logger(name=cubeid.CUBESERVER_NAME, log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBESERVER_NAME, log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidEventListener()

        # params for threading
        self._networking_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

    def run(self):
        self._networking_thread = threading.Thread(target=self._networking_loop)
        self._keep_running = True
        self._networking_thread.start()

        self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self.net.stop()
        self.rfid.stop()

    def _networking_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            #print(":", end="")
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                self.log.debug(f"Received message: ({message.hash}) : {message}")
                if message.msgtype == cm.CubeMsgType.CUBESERVER_SCORESHEET:
                    self.log.info(f"Received scoresheet message from {message.sender}")
                    self.net.acknowledge_message(message)
                self.net.remove_from_incoming_msg_queue(message)
                # TODO: handle other message types

    def add_new_team(self, team: cube_game.CubeTeam) -> bool:
        msg = cm.CubeMsgNewTeam(self.net.node_name, team)
        self.net.send_msg_to_cubeserver(msg)
        return self.net.wait_for_ack(msg)


if __name__ == "__main__":
    import atexit

    fd = CubeFrontDesk()
    atexit.register(fd.stop)
    fd.run()
    try:
        while True:
            time.sleep(1)
            fd.add_new_team(cube_game.CubeTeam(rfid_uid=1234567890, name="Budapest", allocated_time=60.0))
            time.sleep(1)
            fd.add_new_team(cube_game.CubeTeam(rfid_uid=1234567891, name="Paris", allocated_time=160.0))
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeFrontDesk...")
        fd.stop()
