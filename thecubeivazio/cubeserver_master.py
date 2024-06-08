"""
This module handles everything related to TheCube's central room server, i.e. the raspberrypi4
handling the CubeBoxes, the LED matrix displays, and the web page displayed on an HDMI monitor
"""
import signal
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
from thecubeivazio.cube_config import CubeConfig
from thecubeivazio.cube_rgbmatrix_daemon import cube_rgbmatrix_daemon as crd
from thecubeivazio.cube_rgbmatrix_daemon import cube_rgbmatrix_server as crs


class CubeServerMaster:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.CubeLogger(name=cubeid.CUBEMASTER_NODENAME,
                                          log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEMASTER_NODENAME,
                                          log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # load the config
        self.config = CubeConfig.get_config()

        # setup an RGB server
        self.rgb_sender = None

        # params for threading
        self._thread_rfid = threading.Thread(target=self._rfid_loop, daemon=True)
        self._thread_message_handling = threading.Thread(target=self._message_handling_loop, daemon=True)
        self._thread_webpage = threading.Thread(target=self._webpage_loop, daemon=True)
        self._thread_status_update = threading.Thread(target=self._status_update_loop, daemon=True)
        self._thread_rgb = threading.Thread(target=self._rgb_loop, daemon=True)

        self._keep_running = False
        self._last_game_status_sent_to_frontdesk_hash: Optional[Hash] = None
        self._last_teams_status_sent_to_rgb_daemon_hash: Optional[Hash] = None

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self.game_status = cube_game.CubeGameStatus()

        self.net.send_msg_to_frontdesk(
            cm.CubeMsgReplyCubemasterStatus(self.net.node_name, self.game_status))

    def _status_update_loop(self):
        """Periodically performs these actions every time the game status changes:
        - sends the game status to the frontdesk
        - updates the RGBMatrix"""
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            if self._last_game_status_sent_to_frontdesk_hash != self.game_status.hash:
                self.log.info("Game status changed. Updating RGBMatrix and sending game status to frontdesk")
                self.send_status_to_frontdesk()

    def send_status_to_frontdesk(self):
        report = self.net.send_msg_to_frontdesk(
            cm.CubeMsgReplyCubemasterStatus(self.net.node_name, self.game_status),
            require_ack=True, nb_tries=1)
        if not report:
            self.log.error("Failed to send game status to frontdesk")
        else:
            if not report.ok:
                self.log.warning("Sent game status to frontdesk but no ACK received")
            else:
                self.log.success("Sent game status to frontdesk and received ACK")
            self._last_game_status_sent_to_frontdesk_hash = self.game_status.hash

    def _rgb_loop(self):
        """Periodically updates the RGBMatrix"""
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            if self._last_teams_status_sent_to_rgb_daemon_hash != self.teams.hash:
                self.update_rgb()

    # TODO: refactor this system to punctually update the game status instead of having a flag + loop system?
    def update_rgb(self):
        if self.rgb_sender is None:
            if not cube_utils.is_raspberry_pi():
                self.log.warning("Not running on a Raspberry Pi.")
            else:
                self.log.info("Launching RGBMatrix Daemon process")
                crd.CubeRgbMatrixDaemon.launch_process()

            self.log.info("Starting RGBMatrix Daemon")
            self.rgb_sender = crs.CubeRgbServer(is_master=True, debug=True)
            self.log.success("Started RGBMatrix Daemon")

        self.log.info("Updating RGBMatrix Daemon")
        # create a CubeRgbMatrixContentDict from the game status
        all_team_names = CubeConfig.get_config().team_names
        # self.log.critical(f"all_team_names : {all_team_names}")
        rmcd = crs.CubeRgbMatrixContentDict()
        self.log.info(f"We have those teams registered: {[team.name for team in self.teams]}")
        for matrix_id, team_name in enumerate(all_team_names):
            team = self.game_status.teams.get_team_by_name(team_name)
            try:
                assert team
                assert team.end_timestamp is not None
                self.log.info(f"We have team {team_name} with end_timestamp {team.end_timestamp}")
                if self.config.display_team_names_on_rgb:
                    rmcd[matrix_id] = crs.CubeRgbMatrixContent(
                        matrix_id=matrix_id, team_name=team_name, end_timestamp=team.end_timestamp)
                else:
                    rmcd[matrix_id] = crs.CubeRgbMatrixContent(
                        matrix_id=matrix_id, team_name=None, end_timestamp=team.end_timestamp)
            except:
                rmcd[matrix_id] = crs.CubeRgbMatrixContent(
                    matrix_id=matrix_id, team_name=None, end_timestamp=None)
        # send the CubeRgbMatrixContentDict to the server run by the RGBMatrix Daemon
        self.log.info(f"Sending RGBMatrixContentDict to RGBMatrix Daemon : {rmcd.to_string()}")
        rmcd_reconstructed = crs.CubeRgbMatrixContentDict.make_from_string(rmcd.to_string())
        self.log.info(f"Reconstructed RGBMatrixContentDict : {rmcd_reconstructed.to_string()}")
        if self.rgb_sender.send_rgb_matrix_contents_dict(rmcd):
            self.log.success("Sent RGBMatrixContentDict to RGBMatrix Daemon")
            self._last_teams_status_sent_to_rgb_daemon_hash = self.teams.hash
        else:
            self.log.error("Failed to send RGBMatrixContentDict to RGBMatrix Daemon")

    @property
    def teams(self) -> cube_game.CubeTeamsStatusList:
        return self.game_status.teams

    @property
    def cubeboxes(self) -> cube_game.CubeboxesStatusList:
        return self.game_status.cubeboxes

    @teams.setter
    def teams(self, value: cube_game.CubeTeamsStatusList):
        self.game_status.teams = value

    @cubeboxes.setter
    def cubeboxes(self, value: cube_game.CubeboxesStatusList):
        self.game_status.cubeboxes = value

    def run(self):

        self._keep_running = True
        self._thread_rfid.start()
        self._thread_message_handling.start()
        self._thread_webpage.start()
        self._thread_status_update.start()
        self._thread_rgb.start()

    def stop(self):
        self._keep_running = False
        self.net.stop()
        self.rfid.stop()
        self._thread_message_handling.join(timeout=0.1)
        self._thread_rfid.join(timeout=0.1)
        self._thread_webpage.join(timeout=0.1)
        self._thread_rgb.join(timeout=0.1)
        crd.CubeRgbMatrixDaemon.stop_process()
        self.rgb_sender.stop_listening()

    def _message_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
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
                # handle button press messages from the cubeboxes
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_BUTTON_PRESS:
                    self._handle_cubebox_button_press_message(message)
                # handle new team messages from the frontdesk
                elif message.msgtype == cm.CubeMsgTypes.FRONTDESK_NEW_TEAM:
                    self._handle_frontdesk_new_team_message(message)
                elif message.msgtype == cm.CubeMsgTypes.FRONTDESK_REMOVE_TEAM:
                    self._handle_frontdest_remove_team_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_CUBEMASTER_STATUS:
                    self._handle_request_cubemaster_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_ALL_TEAMS_STATUSES:
                    self._handle_request_all_teams_statuses_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUSES:
                    self._handle_request_all_cubeboxes_statuses_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_TEAM_STATUS:
                    self._handle_request_team_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_CUBEMASTER_CUBEBOX_STATUS:
                    self._handle_request_cubebox_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_ALL_TEAMS_STATUS_HASHES:
                    self._handle_request_all_teams_status_hashes_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUS_HASHES:
                    self._handle_request_all_cubeboxes_status_hashes_message(message)
                else:
                    self.log.warning(f"Unhandled message : ({message.hash}) : {message}. Removing")
                self.net.remove_msg_from_incoming_queue(message)

    def register_team_to_cubebox(self, team: cube_game.CubeTeamStatus, new_cubebox_id: CubeId):
        """Register a team to a cubebox. This means updating the team's current cubebox id
        and the cubebox's current team name and starting timestamp"""

        # check if the team is already registered as playing a cubebox.
        # If yes, it means that they resigned their previous cubebox and have moved onto another one.
        # We need to do 2 things :
        # 1. update self.cubebox to record the fact that they've resigned their previous cubebox,
        #    and signal this fact to the cubebox and the frontdesk
        current_cubebox = self.cubeboxes.get_cubebox_by_cube_id(team.current_cubebox_id)
        if current_cubebox:
            # Ok, so this team is currently registered to another cubebox.
            # Record the fact that they've resigned their previous cubebox
            self.log.info(
                f"Team {team.name} is registered to another cubebox : {team.current_cubebox_id}. Abandoning it and switching to cubebox {new_cubebox_id}")
            # NOTE : if another team (team2) is playing this team's (team1) previous cubebox,
            # then this previous cubebox should be configured so as to have team2 as its playing team
            # so if we're here, it means that the previous cubebox is not being played by another team
            team.resign_current_cube()
            current_cubebox.set_state_waiting_for_reset()
            self.cubeboxes.update_cubebox(current_cubebox)
        # now, whatever the case, we just register this team to the cubebox they badged onto
        # update the local cubeboxes teams status lists
        new_cubebox = self.cubeboxes.get_cubebox_by_cube_id(new_cubebox_id)
        new_cubebox.current_team_name = team.name
        # TODO: time.time() or the timestamp from the RFID reader?
        #  I don't think it matters since the timestamps used to compute the scores
        #  are those from the CubeBox, not the CubeMaster
        new_cubebox.start_timestamp = time.time()
        self.cubeboxes.update_cubebox(new_cubebox)
        # update the local teams and cubeboxes status lists
        team.current_cubebox_id = new_cubebox.cube_id
        # if this is the first assignment for this team, also record the start time
        if team.start_timestamp is None:
            team.start_timestamp = new_cubebox.start_timestamp
        self.teams.update_team(team)
        # just checking if the update was successful (it should always be)
        self.log.info(team.to_string())
        team = self.teams.get_team_by_name(team.name)
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
        team = self.teams.get_team_by_rfid_uid(rfid_msg.uid)

        if not team:
            self.log.error(f"RFID UID not matching any known team: {rfid_msg.uid}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return

        self.log.info(f"RFID UID found: {rfid_msg.uid} for team {team.name}")

        # check if the team has already played this cubebox
        if team.has_completed_cube(sending_cubebox_id):
            self.log.error(f"Team {team.name} has already played cubebox {sending_cubebox_id}. Denying.")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.DENIED)
            return

        # check if the team is out of time
        if team.is_time_up():
            self.log.error(f"Team {team.name} is out of time. Denying.")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.DENIED)
            return

        self.register_team_to_cubebox(team, sending_cubebox_id)
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)

    def _handle_cubebox_button_press_message(self, message: cm.CubeMessage):
        self.log.info(f"Received button press message from {message.sender} : {message}")
        # update teams and cubegames to reflect the fact that this cubebox was just won by the team currently playing it
        # first, check if it's a valid button press (i.e. a valid team is currently playing it)
        cubebox: cube_game.CubeboxStatus = self.cubeboxes.get_cubebox_by_node_name(message.sender)
        if not cubebox:
            self.log.error(
                f"WHAT?! Cubebox not found: {message.sender} (THIS SHOULD NEVER HAPPEN. There's bad code somewhere)")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)
            return
        self.log.info(cubebox.to_string())
        self.log.info(self.teams.to_string())
        team = self.teams.get_team_by_current_cube_id(cubebox.cube_id)
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
        self.log.info(
            f"Team {team.name} won cubebox {cubebox.cube_id} in {cbp_msg.press_timestamp - cbp_msg.start_timestamp} seconds. Acknowledging.")
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)

        # update the team's status
        team.set_completed_cube(cubebox.cube_id, cbp_msg.start_timestamp, cbp_msg.press_timestamp)
        team.current_cubebox_id = None
        self.teams.update_team(team)

        self.log.info(f"Teams after button press update : {self.teams.to_string()}")

        # indicate that the cubebox needs to be reset by a staff member
        cubebox.set_state_waiting_for_reset()
        # and update the local cubeboxes teams status lists
        self.cubeboxes.update_cubebox(cubebox)

    def _handle_frontdesk_new_team_message(self, message: cm.CubeMessage):
        self.log.info(f"Received new team message from {message.sender}")
        ntmsg = cm.CubeMsgFrontdeskNewTeam(copy_msg=message)
        self.log.info(f"New team: {ntmsg.team.to_string()}")
        if self.teams.get_team_by_name(ntmsg.team.name):
            self.log.error(f"Team already exists with this name: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OCCUPIED)
            return
        elif self.teams.get_team_by_rfid_uid(ntmsg.team.rfid_uid):
            self.log.error(f"Team already exists with this RFID UID: {ntmsg.team.rfid_uid}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OCCUPIED)
            return
        # ok, so it's a new team. Let's add it to the list
        if self.teams.add_team(ntmsg.team):
            self.log.info(f"Added new team: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
        else:
            self.log.error(f"Failed to add new team: {ntmsg.team.name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)

    def _handle_frontdest_remove_team_message(self, message: cm.CubeMessage):
        self.log.info(f"Received remove team message from {message.sender}")
        rtmsg = cm.CubeMsgFrontdeskRemoveTeam(copy_msg=message)
        self.log.info(f"Remove team: {rtmsg.team_name}")
        team = self.teams.get_team_by_name(rtmsg.team_name)
        if not team:
            self.log.error(f"Team not found: {rtmsg.team_name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
        elif self.teams.remove_team(team.name):
            self.log.info(f"Removed team: {rtmsg.team_name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
        else:
            self.log.error(f"Failed to remove team: {rtmsg.team_name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)

    def _handle_request_cubemaster_status_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request cubemaster status message from {message.sender}")
        self.send_status_to_frontdesk()

    def _handle_request_all_cubeboxes_statuses_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request all cubeboxes status message from {message.sender}")
        self.net.send_msg_to_frontdesk(cm.CubeMsgReplyAllCubeboxesStatuses(self.net.node_name, self.cubeboxes))

    def _handle_request_all_teams_statuses_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request all teams status message from {message.sender}")
        self.net.send_msg_to_frontdesk(cm.CubeMsgReplyAllTeamsStatuses(self.net.node_name, self.teams))

    def _handle_request_team_status_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request team status message from {message.sender}")
        rts_msg = cm.CubeMsgRequestTeamStatus(copy_msg=message)
        team = self.teams.get_team_by_name(rts_msg.team_name)
        if not team:
            self.log.error(f"Team not found: {rts_msg.team_name}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return
        self.net.send_msg_to_frontdesk(cm.CubeMsgReplyTeamStatus(self.net.node_name, team))

    def _handle_request_cubebox_status_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request cubebox status message from {message.sender}")
        rcs_msg = cm.CubeMsgRequestCubeboxStatus(copy_msg=message)
        cubebox = self.cubeboxes.get_cubebox_by_cube_id(rcs_msg.cube_id)
        if not cubebox:
            self.log.error(f"Cubebox not found: {rcs_msg.cube_id}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.INVALID)
            return
        self.net.send_msg_to_frontdesk(cm.CubeMsgReplyCubeboxStatus(self.net.node_name, cubebox))

    def _handle_request_all_teams_status_hashes_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request all teams status hashes message from {message.sender}")
        self.net.send_msg_to_frontdesk(cm.CubeMsgReplyAllTeamsStatusHashes(self.net.node_name, self.teams.hash_dict))

    def _handle_request_all_cubeboxes_status_hashes_message(self, message: cm.CubeMessage):
        self.log.info(f"Received request all cubeboxes status hashes message from {message.sender}")
        self.net.send_msg_to_frontdesk(
            cm.CubeMsgReplyAllCubeboxesStatusHashes(self.net.node_name, self.cubeboxes.hash_dict))

    # TODO
    def _handle_team_time_up(self, team: cube_game.CubeTeamStatus):
        """Handle the fact that a team is out of time"""
        self.log.info(f"Team {team.name} is out of time.")
        if team.use_alarm:
            raise NotImplementedError
        else:
            raise NotImplementedError

    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        self.rfid.run()
        # TODO: re-enable RFID listener on the server once the tests are over
        # TESTING : disable the RFID listener on the server for now
        self.rfid._is_enabled = False
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            for line in self.rfid.get_completed_lines():
                print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                if line.is_valid():
                    # TODO: handle the RFID read message
                    self.log.info("MUST HANDLE CUBEMASTER RFID READ MESSAGE")
                    self.rfid.remove_line(line)

    def _webpage_loop(self):
        # TODO: implement webpage
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            pass


class CubeServerMasterWithPrompt(CubeServerMaster):
    def __init__(self):
        super().__init__()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit : stop the CubeMaster and exit the program")
        print("h, help : display this help")
        print("t, teams : display the list of teams")
        print("cb, cubeboxes : display the list of cubeboxes")
        print("ni, netinfo : display the network nodes info")
        print("wi, whois : send a WhoIs message to all nodes")

    def stop(self):
        super().stop()

    def run(self):
        super().run()
        try:
            self.prompt_loop()
        except KeyboardInterrupt:
            print("KeyboardInterrupt. Stopping the CubeMaster")
            self.stop()

    def prompt_loop(self):
        while True:
            cmd = input("CubeMaster Command > ")
            if not cmd:
                continue
            elif cmd in ["q", "quit"]:
                self.stop()
                break
            elif cmd in ["h", "help"]:
                self.print_help()
            elif cmd in ["t", "teams"]:
                print(self.teams.to_string())
            elif cmd in ["cb", "cubeboxes"]:
                print(self.cubeboxes.to_string())
            elif cmd in ["ni", "netinfo"]:
                # display the nodes in the network and their info
                print(self.net.nodes_list.to_string())
            elif cmd in ["wi", "whois"]:
                self.net.send_msg_to_all(cm.CubeMsgWhoIs(self.net.node_name, cubeid.EVERYONE_NODENAME))
            else:
                print("Unknown command")


def test_rgb():
    import atexit
    master = CubeServerMaster()
    atexit.register(master.stop)

    master.log.setLevel(cube_logger.logging.INFO)
    master.net.log.setLevel(cube_logger.logging.INFO)

    try:
        master.run()

        # create a few sample teams to test the rgb daemon
        sample_teams = [
            cube_game.CubeTeamStatus(
                name="Budapest", rfid_uid="111111", max_time_sec=10, start_timestamp=time.time(), current_cubebox_id=1),
            cube_game.CubeTeamStatus(
                name="Paris", rfid_uid="222222", max_time_sec=20, start_timestamp=time.time(), current_cubebox_id=2),
        ]
        sample_teams = []
        for team in sample_teams:
            master.teams.add_team(team)
        master.log.info(f"Teams registered: {[team.name for team in master.teams]}")

        # master.stop()

        while True:
            master.update_rgb()
            time.sleep(3)



    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeMaster...")
    finally:
        master.stop()
    exit(0)


if __name__ == "__main__":
    test_rgb()
    exit(0)

    import atexit

    master = CubeServerMasterWithPrompt()
    atexit.register(master.stop)

    master.log.setLevel(cube_logger.logging.INFO)
    master.net.log.setLevel(cube_logger.logging.INFO)

    try:
        master.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeMaster...")
    finally:
        master.stop()
