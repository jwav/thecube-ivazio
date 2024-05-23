"""The backend of the cube front desk system. Meant to be implemented by cubegui"""

import threading
import time
from typing import Optional

from thecubeivazio import cube_config

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game

class CubeServerFrontdesk:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.CubeLogger(name=cubeid.CUBEFRONTDESK_NAME, log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEFRONTDESK_NAME, log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # params for threading
        self._msg_handling_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self.config = cube_config.CubeConfig()

        # holds the information about the teams
        self.teams = cube_game.CubeTeamsStatusList()
        self.cubeboxes = cube_game.CubeboxStatusList()

    def run(self):
        self.rfid.run()

        self._msg_handling_thread = threading.Thread(target=self._msg_handling_loop)
        self._keep_running = True
        self._msg_handling_thread.start()

        #self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self._keep_running = False
        self.net.stop()
        self.rfid.stop()
        self._msg_handling_thread.join(timeout=0.1)


    def _msg_handling_loop(self):
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
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                elif message.msgtype == cm.CubeMsgTypes.CUBEMASTER_SCORESHEET:
                    self.log.info(f"Received scoresheet message from {message.sender}")
                    self.net.acknowledge_this_message(message)
                elif message.msgtype == cm.CubeMsgTypes.CUBEMASTER_TEAM_WIN:
                    self.log.info(f"Received team win message from {message.sender}")
                    # TODO: do something with it
                    # TODO: wait, the Frontdesk can already receive the team win message from the CubeBox if we're on UDP broadcast
                    #  should i handle it anyway just in case i move to TCP or addressed UDP later on?
                    self.net.acknowledge_this_message(message)
                else:
                    self.log.warning(f"Unhandled message type: {message.msgtype}. Removing")
                    self.net.remove_msg_from_incoming_queue(message)
                # TODO: handle other message types

    def add_new_team(self, team: cube_game.CubeTeamStatus) -> cubenet.SendReport:
        """Send a message to the CubeMaster to add a new team. Return True if the CubeMaster added the team, False if not, None if no response."""
        msg = cm.CubeMsgNewTeam(self.net.node_name, team)
        report = self.net.send_msg_to_cubeserver(msg, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the new team message : {team.name}")
            return report
        ack_msg = report.ack_msg
        self.log.debug(f"add_new_team ack_msg={ack_msg.to_string() if ack_msg else None}")
        if ack_msg is None:
            self.log.error(f"The CubeMaster did not respond to the new team message : {team.name}")
        elif ack_msg.info == cm.CubeAckInfos.OK:
            self.log.info(f"The CubeMaster added the new team : {team.name}")
        else:
            self.log.error(f"The CubeMaster did not add the new team : {team.name} ; info={ack_msg.info}")
        return report



if __name__ == "__main__":
    import atexit

    team_names = ["Budapest",
                  "Debrecen",
                  "Budapest",
                    "Szeged",
                    "Pécs",
                  "Debrecen",
                  "Zalaegerszeg",]

    fd = CubeServerFrontdesk()
    atexit.register(fd.stop)
    fd.run()
    try:
        for team_name in team_names:
            fd.add_new_team(cube_game.CubeTeamStatus(rfid_uid="1234567890", name=team_name, max_time_sec=60.0))
            time.sleep(5)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeFrontDesk...")
    finally:
        fd.stop()
