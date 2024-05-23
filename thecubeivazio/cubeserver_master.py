"""
This module handles everything related to TheCube's central room server, i.e. the raspberrypi4
handling the CubeBoxes, the LED matrix displays, and the web page displayed on an HDMI monitor
"""
import threading
import time

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game
from thecubeivazio import cube_messages as cm
from thecubeivazio.cube_common_defines import *


class CubeServerMaster:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.CubeLogger(name=cubeid.CUBEMASTER_NAME,
                                           log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEMASTER_NAME,
                                          log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # params for threading
        self._rfid_thread = None
        self._networking_thread = None
        self._webpage_thread = None
        self._display_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self.teams = cube_game.CubeTeamsStatusList()
        self.cubeboxes = cube_game.CubeboxStatusList()

    def run(self):
        self._rfid_thread = threading.Thread(target=self._rfid_loop)
        self._networking_thread = threading.Thread(target=self._message_handling_loop)
        self._webpage_thread = threading.Thread(target=self._webpage_loop)
        self._display_thread = threading.Thread(target=self._display_loop)
        self._keep_running = True
        self._rfid_thread.start()
        self._networking_thread.start()
        self._webpage_thread.start()
        self._display_thread.start()

        #self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self.net.stop()
        self.rfid.stop()
        self._keep_running = False
        self._networking_thread.join(timeout=0.1)
        self._rfid_thread.join(timeout=0.1)
        self._webpage_thread.join(timeout=0.1)
        self._display_thread.join(timeout=0.1)

    def _message_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                # ignore ACK messages. They are to be handled in wait_for_ack_of()
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                # handle RFID read messages from the cubeboxes
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_RFID_READ:
                    self._handle_cubebox_rfid_read_message(message)
                    continue
                # handle button press messages from the cubeboxes
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_BUTTON_PRESS:
                    self._handle_cubebox_button_press_message(message)
                    continue
                # handle new team messages from the frontdesk
                elif message.msgtype == cm.CubeMsgTypes.FRONTDESK_NEW_TEAM:
                    self._handle_frontdesk_new_team_message(message)
                    continue

                else:
                    self.log.warning(f"Unhandled message : ({message.hash}) : {message}. Removing")
                    self.net.remove_msg_from_incoming_queue(message)

    def register_team_to_cubebox(self, team: cube_game.CubeTeamStatus, cubebox_id: CubeboxId):
        """Register a team to a cubebox. This means updating the team's current cubebox id
        and the cubebox's current team name and starting timestamp"""

        # check if the team is already registered as playing a cubebox.
        # If yes, it means that they resigned their previous cubebox and have moved onto another one.
        # We need to do 2 things :
        # 1. update self.cubebox to record the fact that they've resigned their previous cubebox,
        #    and signal this fact to the cubebox and the frontdesk
        current_cubebox = self.cubeboxes.find_cubebox_by_cube_id(team.current_cubebox_id)
        if current_cubebox:
            # Ok, so this team is currently registered to another cubebox.
            # Record the fact that they've resigned their previous cubebox
            self.log.info(
                f"Team {team.name} is registered to another cubebox : {team.current_cubebox_id}. Abandoning it and switching to cubebox {new_cubebox.cube_id}")
            # NOTE : if another team (team2) is playing this team's (team1) previous cubebox,
            # then this previous cubebox should be configured so as to have team2 as its playing team
            # so if we're here, it means that the previous cubebox is not being played by another team
            team.resign_current_cube()
            current_cubebox.set_state_waiting_for_reset()
            self.cubeboxes.update_cubebox(current_cubebox)
        # now, whatever the case, we just register this team to the cubebox they badged onto
        # update the local cubeboxes teams status lists
        new_cubebox = self.cubeboxes.find_cubebox_by_cube_id(cubebox_id)
        new_cubebox.current_team_name = team.name
        # TODO: time.time() or the timestamp from the RFID reader?
        #  I don't think it matters since the timestamps used to compute the scores
        #  are those from the CubeBox, not the CubeMaster
        new_cubebox.starting_timestamp = time.time()
        self.cubeboxes.update_cubebox(new_cubebox)
        # update the local teams and cubeboxes status lists
        team.current_cubebox_id = new_cubebox.cube_id
        # if this is the first assignment for this team, also record the start time
        if team.starting_timestamp is None:
            team.starting_timestamp = new_cubebox.starting_timestamp
        self.teams.update_team(team)
        # just checking if the update was successful (it should always be)
        self.log.info(team.to_string())
        team = self.teams.find_team_by_name(team.name)
        self.log.info(f"Team {team.name} is registered as playing cubebox {team.current_cubebox_id}")
        self.log.info(team.to_string())

    def _handle_cubebox_rfid_read_message(self, message: cm.CubeMessage):
        self.log.info(f"Received RFID read message from {message.sender}")
        rfid_msg = cm.CubeMsgRfidRead(copy_msg=message)
        sending_cubebox_id = cubeid.node_name_to_cubebox_index(message.sender)
        if not sending_cubebox_id in cubeid.CUBEBOX_IDS:
            self.log.error(f"Invalid sender: {message.sender}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return
        # check if the rfid uid matches one of the registered teams
        team = self.teams.find_team_by_rfid_uid(rfid_msg.uid)

        if not team:
            self.log.error(f"RFID UID not matching any known team: {rfid_msg.uid}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return

        self.log.info(f"RFID UID found: {rfid_msg.uid} for team {team.name}")

        # check if the team has already played this cubebox
        if team.has_played_cube(sending_cubebox_id):
            self.log.error(f"Team {team.name} has already played cubebox {sending_cubebox_id}. Denying.")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.DENIED)
            return

        self.register_team_to_cubebox(team, sending_cubebox_id)
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)

    def _handle_cubebox_button_press_message(self, message: cm.CubeMessage):
        self.log.info(f"Received button press message from {message.sender} : {message}")
        # update teams and cubegames to reflect the fact that this cubebox was just won by the team currently playing it
        # first, check if it's a valid button press (i.e. a valid team is currently playing it)
        cubebox: cube_game.CubeboxStatus = self.cubeboxes.find_cubebox_by_node_name(message.sender)
        if not cubebox:
            self.log.error(
                f"WHAT?! Cubebox not found: {message.sender} (this should NOT happen. There's bad code somewhere)")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)
            return
        self.log.info(cubebox.to_string())
        self.log.info(self.teams.to_string())
        team = self.teams.find_team_by_current_cube_id(cubebox.cube_id)
        if not team:
            self.log.error(f"No team is playing that cubebox: {cubebox.cube_id}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return
        cbp_msg = cm.CubeMsgButtonPress(copy_msg=message)
        self.log.info(f"CubeMsgButtonPress : {cbp_msg.to_string()}")
        if not cbp_msg.has_valid_times():
            self.log.error(f"Invalid button press message: {cbp_msg}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return
        # ok, it's a valid button press, which means a team is playing this cubebox.
        # Let's record that win. But first, acknowledge the message to the cubebox
        self.log.info(f"Team {team.name} won cubebox {cubebox.cube_id} in {cbp_msg.press_timestamp - cbp_msg.start_timestamp} seconds. Acknowledging.")
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)

        # update the team's status
        team.set_completed_cube(cubebox.cube_id, cbp_msg.start_timestamp, cbp_msg.press_timestamp)
        team.current_cubebox_id = None
        self.teams.update_team(team)

        self.log.info(f"Teams after win update : {self.teams.to_string()}")

        # indicate that the cubebox needs to be reset by a staff member
        cubebox.set_state_waiting_for_reset()
        # and update the local cubeboxes teams status lists
        self.cubeboxes.update_cubebox(cubebox)

        # now notify the front desk of the win
        win_msg = cm.CubeMsgCubeboxWin(self.net.node_name, team.name, cubebox.cube_id,
                                       cbp_msg.start_timestamp, cbp_msg.press_timestamp)
        report = self.net.send_msg_to_frontdesk(win_msg, require_ack=True)
        if not report:
            self.log.error(f"Failed to send cubebox win message to frontdesk")
            return
        ack_msg = report.ack_msg
        if not ack_msg:
            self.log.error(f"Sent cubebox win message to frontdesk but no ack received")
            return
        else:
            self.log.info(f"Cubebox win message sent to and acked by frontdesk")

    def _handle_frontdesk_new_team_message(self, message: cm.CubeMessage):
        self.log.info(f"Received new team message from {message.sender}")
        ntmsg = cm.CubeMsgNewTeam(copy_msg=message)
        self.log.info(f"New team: {ntmsg.team.to_string()}")
        if self.teams.find_team_by_name(ntmsg.team.name):
            self.log.error(f"Team already exists: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OCCUPIED)
        elif self.teams.add_team(ntmsg.team):
            self.log.info(f"Added new team: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
        else:
            self.log.error(f"Failed to add new team: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)

    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        # TODO: re-enable RFID listener on the server once the tests are over
        # TESTING : disable the RFID listener on the server for now
        return
        self.rfid.run()
        while self._keep_running:
            for line in self.rfid.get_completed_lines():
                print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                if line.is_valid():
                    # TODO: handle the RFID read message
                    self.log.info("MUST HANDLE CUBEMASTER RFID READ MESSAGE")
                    self.rfid.remove_line(line)

    def _display_loop(self):
        # TODO: implement LCD matrix display
        while self._keep_running:
            pass

    def _webpage_loop(self):
        # TODO: implement webpage
        while self._keep_running:
            pass


class CubeServerMasterWithPrompt:
    def __init__(self):
        self.csm = CubeServerMaster()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit: stops the CubeMaster")
        print("h, help: prints this help message")
        print("ni, netinfo: prints the network information")
        print("wi, whois: sends WHO_IS message to everyone")
        print("t, teams: prints the list of teams")
        print("cg: show cubegames")
        print("ogs: overall game status")

    def stop(self):
        self.csm.stop()

    def run(self):
        self.csm.run()
        while True:
            cmd = input("CubeMaster Command > ")
            if not cmd:
                continue
            elif cmd in ["q", "quit"]:
                self.stop()
                break
            elif cmd in ["h", "help"]:
                self.print_help()
            elif cmd in ["g", "games"]:
                print("Not implemented yet")
            elif cmd in ["t", "teams"]:
                print(self.csm.teams.to_string())
            elif cmd in ["cg", "cubegames"]:
                print(self.csm.cubeboxes.to_string())
            elif cmd in ["ni", "netinfo"]:
                # display the nodes in the network and their info
                print(self.csm.net.nodes_list.to_string())
            elif cmd in ["wi", "whois"]:
                self.csm.net.send_msg_to_all(cm.CubeMsgWhoIs(self.csm.net.node_name, cubeid.EVERYONE_NAME))
            else:
                print("Unknown command")


if __name__ == "__main__":
    import atexit

    master = CubeServerMasterWithPrompt()
    atexit.register(master.stop)
    try:
        master.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeMaster...")
    finally:
        master.stop()
