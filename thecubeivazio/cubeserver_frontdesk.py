"""The backend of the cube front desk system. Meant to be implemented by cubegui"""
import logging
import threading
import time
from typing import Optional, Iterable, Sized

from thecubeivazio import cube_config

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game
from thecubeivazio.cube_common_defines import *
from thecubeivazio import cube_database as cubedb
from thecubeivazio.cubeserver_cubemaster import CubeServerMaster


class CubeServerFrontdesk:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.CubeLogger(name=cubeid.CUBEFRONTDESK_NODENAME,
                                          log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # load the config
        self.config = cube_config.CubeConfig()

        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEFRONTDESK_NODENAME,
                                          log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # params for threading
        self._msg_handling_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        # holds the information about the teams
        # TODO: do something with them. update them, request updates, etc
        self.game_status = cube_game.CubeGameStatus()

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
        self.rfid.run()
        self._msg_handling_thread = threading.Thread(target=self._msg_handling_loop)
        self._keep_running = True
        self._msg_handling_thread.start()
        # self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self._keep_running = False
        self.net.stop()
        self.rfid.stop()
        self._msg_handling_thread.join(timeout=0.1)

    def _msg_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            # print(":", end="")
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                # ignore ack messages, they're handled in the networking module
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_BUTTON_PRESS:
                    self._handle_cubebox_button_press_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_CUBEBOX_STATUS:
                    self._handle_reply_cubebox_status(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_TEAM_STATUS:
                    self._handle_reply_team_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_ALL_CUBEBOXES_STATUSES:
                    self._handle_reply_all_cubeboxes_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_ALL_TEAMS_STATUSES:
                    self._handle_reply_all_teams_status(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_CUBEMASTER_STATUS:
                    self._handle_reply_cubemaster_status_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_ALL_TEAMS_STATUS_HASHES:
                    self._handle_reply_all_teams_status_hashes(message)
                elif message.msgtype == cm.CubeMsgTypes.REPLY_ALL_CUBEBOXES_STATUS_HASHES:
                    self._handle_reply_all_cubeboxes_status_hashes(message)
                # TODO: handle other message types
                else:
                    self.log.warning(f"Unhandled message type: {message.msgtype}. Removing")
                self.net.remove_msg_from_incoming_queue(message)

    def _handle_reply_all_cubeboxes_status_hashes(self, message: cm.CubeMessage):
        raise NotImplementedError

    def _handle_reply_all_teams_status_hashes(self, message: cm.CubeMessage):
        raise NotImplementedError

    def _handle_cubemaster_cubebox_status_message(self, message: cm.CubeMessage):
        raise NotImplementedError

    def _handle_reply_all_teams_status(self, message: cm.CubeMessage) -> bool:
        try:
            self.log.info(f"Received reply all teams status message from {message.sender}")
            alsr_msg = cm.CubeMsgReplyAllTeamsStatuses(copy_msg=message)
            new_teams = alsr_msg.teams_statuses
            assert new_teams, "_handle_reply_all_teams_status: new_teams is None"
            assert self.teams.update_from_teams_list(
                new_teams), "_handle_reply_all_teams_status: update_from_teams_list failed"
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
            return True
        except Exception as e:
            self.log.error(f"Error handling reply all teams status message: {e}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.ERROR)
            return False

    def _handle_reply_team_status_message(self, message: cm.CubeMessage) -> bool:
        try:
            self.log.info(f"Received team status reply message from {message.sender}")
            rts_msg = cm.CubeMsgReplyTeamStatus(copy_msg=message)
            new_team_status = rts_msg.team_status
            assert new_team_status.is_valid(), "_handle_team_status_reply: new_team_status is invalid"
            assert self.teams.update_team(new_team_status), "_handle_team_status_reply: update_team failed"
            self.log.info(f"Updated team status: {new_team_status}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
            return True
        except Exception as e:
            self.log.error(f"Error handling team status reply message: {e}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.INVALID)
            return False

    def _handle_reply_all_cubeboxes_status_message(self, message: cm.CubeMessage) -> bool:
        try:
            self.log.info(f"Received reply all cubeboxes status message from {message.sender}")
            acsr_msg = cm.CubeMsgReplyAllCubeboxesStatuses(copy_msg=message)
            new_cubeboxes = acsr_msg.cubeboxes_statuses
            assert new_cubeboxes, "_handle_reply_all_cubeboxes_status: new_cubeboxes is None"
            assert self.cubeboxes.update_from_cubeboxes(
                new_cubeboxes), "_handle_reply_all_cubeboxes_status: update_from_cubeboxes_list failed"
            report = self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
            assert report.sent_ok, "_handle_reply_all_cubeboxes_status: acknowledge_this_message failed"
            return True
        except Exception as e:
            self.log.error(f"Error handling reply all cubeboxes status message: {e}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.ERROR)
            return False

    @cubetry
    def _handle_reply_cubebox_status(self, message: cm.CubeMessage) -> bool:
        self.log.info(f"Received reply cubebox status message from {message.sender}")
        acsr_msg = cm.CubeMsgReplyCubeboxStatus(copy_msg=message)
        new_cubebox = acsr_msg.cubebox
        assert new_cubebox, "_handle_reply_cubebox_status: new_cubebox is None"
        assert self.cubeboxes.update_from_cubebox(new_cubebox), "_handle_reply_cubebox_status: update_cubebox failed"
        self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
        return True

    def _handle_reply_cubemaster_status_message(self, message: cm.CubeMessage) -> bool:
        try:
            self.log.info(f"Received reply cubemaster status message from {message.sender}")
            acsr_msg = cm.CubeMsgReplyCubemasterStatus(copy_msg=message)
            new_cubemaster_status = acsr_msg.cubemaster_status
            assert new_cubemaster_status, "_handle_reply_cubemaster_status: new_cubemaster is None"
            assert new_cubemaster_status.teams is not None, "_handle_reply_cubemaster_status: new_cubemaster.teams is None"
            assert new_cubemaster_status.teams.is_valid(), "_handle_reply_cubemaster_status: new_cubemaster.teams is invalid"
            assert new_cubemaster_status.cubeboxes, "_handle_reply_cubemaster_status: new_cubemaster.cubeboxes is None"
            assert new_cubemaster_status.cubeboxes is not None, "_handle_reply_cubemaster_status: new_cubemaster.cubeboxes is None"
            assert new_cubemaster_status.cubeboxes.is_valid(), "_handle_reply_cubemaster_status: new_cubemaster.cubeboxes is invalid"
            assert self.teams.update_from_teams_list(
                new_cubemaster_status.teams), "_handle_reply_cubemaster_status: update_from_teams_list failed"
            assert self.cubeboxes.update_from_cubeboxes(
                new_cubemaster_status.cubeboxes), "_handle_reply_cubemaster_status: update_from_cubeboxes failed"
            self.log.success(f"Updated teams and cubeboxes from cubemaster status")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
            self.log.info(f"new cubemaster status: {new_cubemaster_status.to_json()}")
            self.log.info(f"new frontdesk teams statuses: {self.teams.to_json()}")
            self.log.info(f"new frontdesk cubeboxes statuses: {self.cubeboxes.to_json()}")
            return True
        except Exception as e:
            self.log.error(f"Error handling reply cubemaster status message: {e}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.ERROR)
            return False

    def _handle_cubebox_button_press_message(self, message: cm.CubeMessage):
        self.log.info(f"Received team win message from {message.sender}")
        try:
            cbp_msg = cm.CubeMsgButtonPress(copy_msg=message)
            assert cbp_msg.is_valid(), "Invalid CubeMsgButtonPress message"
            cube_id = cbp_msg.cube_id
            team_name = self.teams.get_team_by_current_cube_id(cube_id).name
            assert team_name, f"Team not found for cube_id {cube_id}"
            win_timestamp = cbp_msg.press_timestamp
            self.game_status.register_win(cube_id, team_name, win_timestamp)
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
        except Exception as e:
            self.log.error(f"Error handling cubebox button press message: {e}")
            self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.ERROR)

    @cubetry
    def add_new_team(self, team: cube_game.CubeTeamStatus) -> cubenet.SendReport:
        """Send a message to the CubeMaster to add a new team. Return True if the CubeMaster added the team, False if not, None if no response."""
        msg = cm.CubeMsgFrontdeskNewTeam(self.net.node_name, team)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the new team message : {team.name}")
            return report
        ack_msg = report.ack_msg
        self.log.debug(f"add_new_team ack_msg={ack_msg.to_string() if ack_msg else None}")
        if ack_msg is None:
            self.log.error(f"The CubeMaster did not respond to the new team message : {team.name}")
        elif ack_msg.info == cm.CubeAckInfos.OK:
            self.log.info(f"The CubeMaster added the new team : {team.name}")
            self.teams.add_team(team)
        else:
            self.log.error(f"The CubeMaster did not add the new team : {team.name} ; info={ack_msg.info}")
        return report

    @cubetry
    def send_full_command(self, full_command:str) -> bool:
        """Send a full command to the CubeMaster. Returns True if the command was sent, False if not."""
        self.log.info(f"Sending full command: {full_command}")
        msg = cm.CubeMsgCommand(self.net.node_name, full_command=full_command)
        self.log.critical(f"words={msg.words}")
        destination_node = msg.target
        if destination_node not in cubeid.ALL_NODENAMES:
            self.log.error(f"Invalid destination node: {destination_node}")
            return False
        report = self.net.send_msg_to(msg, destination_node, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the full command : {full_command}")
            return False
        if not report.ack_ok:
            self.log.error(f"Node {destination_node} did not acknowledge the full command : {full_command}")
            return False
        self.log.success(f"Node {destination_node} acknowledged the full command : {full_command}")
        return True

    @cubetry
    def move_team_to_database(self, team_name) -> bool:
        """Move a team from the status to the database."""
        try:
            team = self.teams.get_team_by_name(team_name)
            assert team, f"Team {team_name} not found"
            assert cube_game.CubeTeamsStatusList.add_team_to_database(
                team), f"Failed to add team {team_name} to the database"
            self.teams.remove_team(team_name)
            self.log.info(f"Moved team {team_name} to the database")
            return True
        except Exception as e:
            self.log.error(f"Error moving team {team_name} to the database: {e}")
            return False

    @cubetry
    def request_all_cubeboxes_statuses_one_by_one(self, reply_timeout: Seconds = None) -> bool:
        """Send a message to the CubeMaster to request the status of all cubeboxes one by one.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        for cubebox_id in cubeid.CUBEBOX_IDS:
            self.log.info(f"Requesting cubebox status for cubebox {cubebox_id}")
            if not self.request_cubebox_status(cubebox_id, reply_timeout):
                self.log.warning(
                    f"No response from cubebox {cubebox_id}. Ending request_all_cubeboxes_statuses_one_by_one")
                return False
            else:
                self.log.success(f"Received status reply from cubebox {cubebox_id}")
        self.log.success("All cubeboxes statuses requested")
        return True

    @cubetry
    def order_cubemaster_to_delete_team(self, team) -> Optional[bool]:
        """Send a message to the CubeMaster to delete a team.
        Return True if the CubeMaster deleted the team, False if not, None if no response.
        If the Cubemaster deleted the team, remove it from the frontdesk status."""
        # first, check that it's a team in our current status, and not one from the database.
        # We never delete from the database
        if not self.teams.has_team(team):
            self.log.error(f"Team {team.name} not found in the current status")
            return False
        msg = cm.CubeMsgFrontdeskDeleteTeam(self.net.node_name, team_name=team.name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the delete team message : {team.name}")
            return False
        if not report.ack_ok:
            self.log.error(f"The CubeMaster did not respond to the delete team message : {team.name}")
            return None
        self.log.success(f"The CubeMaster deleted the team : {team.name}")
        self.teams.remove_team(team.name)
        return True

    @cubetry
    def order_cubebox_to_reset(self, cubebox_id: int) -> bool:
        """Send a message to a CubeBox to reset itself. Returns True if the msg has been sent,
        we're not waiting for a reply."""
        self.log.info(f"Sending cubebox reset order message for cubebox {cubebox_id}")
        cubebox_nodename = cubeid.cubebox_index_to_node_name(cubebox_id)
        msg = cm.CubeMsgOrderCubeboxToReset(self.net.node_name, cubebox_id)
        report = self.net.send_msg_to(msg, cubebox_nodename, require_ack=False)
        if not report:
            self.log.error(f"Failed to send the cubebox reset message for cubebox {cubebox_id}")
            return False
        self.log.info(f"Sent cubebox reset message for cubebox {cubebox_id}")
        return True

    @cubetry
    def order_cubebox_to_wait_for_reset(self, cubebox_id: int) -> bool:
        """Send a message to a CubeBox to wait for a reset. Returns True if the msg has been sent,
        we're not waiting for a reply."""
        self.log.info(f"Sending cubebox wait for reset order message for cubebox {cubebox_id}")
        msg = cm.CubeMsgOrderCubeboxToWaitForReset(self.net.node_name, cubebox_id)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error(f"Failed to send the cubebox wait for reset message for cubebox {cubebox_id}")
            return False
        self.log.info(f"Sent cubebox wait for reset message for cubebox {cubebox_id}")
        return True

    @cubetry
    def request_cubemaster_status(self, reply_timeout: Seconds) -> bool:
        """Send a message to the CubeMaster to request its status.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestCubemasterStatus(self.net.node_name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error("Failed to send the request cubemaster status message")
            return False

        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_CUBEMASTER_STATUS,
                                                  timeout=reply_timeout)
            if not reply_msg:
                self.log.error("Failed to receive the cubemaster status reply")
                return False
            return self._handle_reply_cubemaster_status_message(reply_msg)

    @cubetry
    def send_config_message_to_all(self, config: cube_config.CubeConfig=None, nodenames:list[NodeName]=cubeid.ALL_NODENAMES) -> cubenet.SendReport:
        """Send a message to all nodes with the new config"""
        # first of all, save this config as an encrypted file
        config = config or self.config
        if not self.config.save_to_encrypted_json_file():
            return cubenet.SendReport(sent_ok=False, raw_info="Failed to save the config to file")
        self.log.info(f"Sending config message to all nodes : {nodenames}...")

        msg = cm.CubeMsgConfig(self.net.node_name, config)
        # we have to do this node by node, checking that everyone acks
        for node_name in nodenames:
            # don't send to self
            if node_name == self.net.node_name:
                continue
            self.log.info(f"Sending config message to {node_name}...")
            report = self.net.send_msg_to(msg, node_name, require_ack=False)
            if not report.sent_ok:
                self.log.error(f"Failed to send the config message to {node_name}")
                return cubenet.SendReport(sent_ok=False, raw_info=f"Failed to send the config message to {node_name}")
            ack_msg = self.net.wait_for_ack_of(msg, ack_sender=node_name)
            if not ack_msg:
                self.log.error(f"Timed out waiting for ack from {node_name}.")
                return cubenet.SendReport(sent_ok=False, raw_info=f"Timed out waiting for ack from {node_name}")
            if ack_msg.info != cm.CubeAckInfos.OK:
                self.log.error(f"{node_name} acked but with info {ack_msg.info}")
                return cubenet.SendReport(sent_ok=False, raw_info=f"{node_name} acked but with info {ack_msg.info}")
            self.log.success(f"Sent config message to {node_name}")
        self.log.success(f"Sent config message to all nodes")
        return cubenet.SendReport(sent_ok=True)

    @cubetry
    def request_team_status(self, team_name: str, reply_timeout: Optional[Seconds]) -> bool:
        """Send a message to the CubeMaster to request the status of a team.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestTeamStatus(self.net.node_name, team_name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error(f"Failed to send the request team status message for team {team_name}")
            return True
        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_TEAM_STATUS, timeout=reply_timeout)
            if not reply_msg:
                self.log.error(f"Failed to receive the team status reply for team {team_name}")
                return False
            return self._handle_reply_team_status_message(reply_msg)

    @cubetry
    def request_all_teams_status(self, reply_timeout: Optional[Seconds]) -> bool:
        """Send a message to the CubeMaster to request the status of all teams.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestAllTeamsStatuses(self.net.node_name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error("Failed to send the request all teams status message")
            return True
        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_TEAM_STATUS, timeout=reply_timeout)
            if not reply_msg:
                self.log.error("Failed to receive the all teams status reply")
                return False
            return self._handle_reply_all_teams_status(reply_msg)

    @cubetry
    def request_all_teams_status_hashes(self, reply_timeout: Optional[Seconds]) -> bool:
        """Send a message to the CubeMaster to request the status hashes of all teams.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestAllTeamsStatusHashes(self.net.node_name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error("Failed to send the request all teams status hashes message")
            return True
        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_ALL_TEAMS_STATUS_HASHES,
                                                  timeout=reply_timeout)
            if not reply_msg:
                self.log.error("Failed to receive the all teams status hashes reply")
                return False
            return self._handle_reply_all_teams_status_hashes(reply_msg)

    @cubetry
    def request_cubebox_status(self, cubebox_id: int, reply_timeout: Seconds = None) -> bool:
        """Send a message to a CubeBox to request its status.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestCubeboxStatus(self.net.node_name, cubebox_id)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error(f"Failed to send the request cubebox status message for cubebox {cubebox_id}")
            return True
        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_CUBEBOX_STATUS, timeout=reply_timeout)
            if not reply_msg:
                self.log.error(f"Failed to receive the cubebox status reply for cubebox {cubebox_id}")
                return False
            return self._handle_reply_cubebox_status(reply_msg)

    @cubetry
    def request_all_cubeboxes_status_hashes(self, reply_timeout: Seconds = None) -> bool:
        """Send a message to the CubeMaster to request the status hashes of all cubeboxes.
        if a reply_timout is specified, wait for the reply for that amount of time.
        If the request send or the reply receive fails, return False."""
        msg = cm.CubeMsgRequestAllCubeboxesStatusHashes(self.net.node_name)
        report = self.net.send_msg_to_cubemaster(msg, require_ack=False)
        if not report:
            self.log.error("Failed to send the request all cubeboxes status hashes message")
            return True
        if reply_timeout is not None:
            reply_msg = self.net.wait_for_message(msgtype=cm.CubeMsgTypes.REPLY_ALL_CUBEBOXES_STATUS_HASHES,
                                                  timeout=reply_timeout)
            if not reply_msg:
                self.log.error("Failed to receive the all cubeboxes status hashes reply")
                return False
            return self._handle_reply_all_cubeboxes_status_hashes(reply_msg)


class CubeServerFrontdeskWithPrompt(CubeServerFrontdesk):
    def __init__(self):
        super().__init__()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit : stop the CubeFrontdesk and exit the program")
        print("h, help : display this help")
        print("t, teams : display the list of teams")
        print("cb, cubeboxes : display the list of cubeboxes")
        print("ni, netinfo : display the network nodes info")
        print("wi, whois : send a WhoIs message to all nodes")
        print("at, addteam (name [, custom_name, uid, max_time_sec]) : add a new team")
        print("atr, addtrophy (team_name, name [, points, description, image_path]) : add a new trophy")
        print("rcms, requestcubemasterstatus : request the CubeMaster status")
        print("rts, requestteamstatus (team_name) : request the team status")
        print("rats, requestallteamsstatus : request the status of all teams")
        print("rbs, requestcubeboxstatus (cubebox_id) : request the cubebox status")
        print("rabs, requestallcubeboxstatus : request the status of all cubeboxes")

    def stop(self):
        super().stop()

    def run(self, no_prompt=False):
        super().run()
        # stop the rfid listener since we're gonna press the enter key a lot while using the prompt
        self.rfid.stop()
        if no_prompt:
            return
        try:
            self.prompt_loop()
        except KeyboardInterrupt:
            print("KeyboardInterrupt. Stopping the CubeFrontdesk")
            self.stop()

    @staticmethod
    def pad_args(argslist: Sized, *defaults):
        ret = list(argslist) + list(defaults)
        print(f"pad_args: {ret}")
        return ret

    def prompt_loop(self):
        while True:
            line = input("CubeFrontdesk Command > ")
            self.handle_input(line)

    def handle_input(self, line: str) -> bool:
        cmd = line.split()[0] if line else None
        args = line.split()[1:]
        if not cmd:
            return True
        elif cmd in ["q", "quit"]:
            self.stop()
            return True
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
        elif cmd in ["at", "addteam"]:
            if len(args) < 3:
                print("Usage: addteam (name [, custom_name, uid, max_time_sec])")
                return False
            # if there are less than 4 args, pad the rest with default values until there are 4 args
            args = self.pad_args(args, "CustomName", "1234567890", 60.0)
            name, custom_name, uid, max_time_sec = args

            max_time_sec = Seconds(max_time_sec)
            team = cube_game.CubeTeamStatus(rfid_uid=uid, name=name, custom_name=custom_name, max_time_sec=max_time_sec)
            self.add_new_team(team)
        elif cmd in ["atr", "addtrophy"]:
            if len(args) < 2:
                print("Usage: ddtrophy (team_name, name [, points, description, image_path])")
                return False
            args = self.pad_args(args, 100, "FooDescription", "foo.png")
            team_name, name, points, description, image_path = args
            team = self.teams.get_team_by_name(team_name)
            if team is None:
                print(f"Team {team_name} not found")
                return False
            points = int(points)
            trophy = cube_game.CubeTrophy(name=name, description=description, points=points, image_filename=image_path)
            team.trophies_names.append(trophy)
            self.log.info(f"Added trophy {trophy.name} to team {team.name}:")
            self.log.info(f"{team}")
        elif cmd in ["rcms", "requestcubemasterstatus"]:
            self.request_cubemaster_status()
        elif cmd in ["rts", "requestteamstatus"]:
            if len(args) < 1:
                print("Usage: requestteamstatus (team_name)")
                return False
            team_name = args[0]
            self.request_team_status(team_name, reply_timeout=STATUS_REPLY_TIMEOUT)
        elif cmd in ["rats", "requestallteamsstatus"]:
            self.request_all_teams_status(reply_timeout=STATUS_REPLY_TIMEOUT)
        # elif cmd in ["rabs", "requestallcubeboxstatus"]:
        #     self.request_all_cubeboxes_statuses_at_once()
        else:
            print("Unknown command")
            return False


def test():
    import atexit
    fd = CubeServerFrontdesk()
    atexit.register(fd.stop)

    team_names = ["Budapest",
                  "Debrecen",
                  "Budapest",
                  "Szeged",
                  "Pécs",
                  "Debrecen",
                  "Zalaegerszeg", ]
    for team_name in team_names:
        fd.add_new_team(cube_game.CubeTeamStatus(rfid_uid="1234567890", name=team_name, max_time_sec=60.0))
    time.sleep(5)


def test_prompt_commands():
    import atexit
    fd = CubeServerFrontdeskWithPrompt()
    atexit.register(fd.stop)

    fd.run(no_prompt=True)
    fd.handle_input("at London")


def generate_sample_teams() -> cube_game.CubeTeamsStatusList:
    from datetime import datetime, timedelta

    teams = cube_game.CubeTeamsStatusList()

    # Lists of parameters for each team
    names = ["Dakar", "Paris", "Tokyo", "New York", "London"]
    custom_names = ["Riri & Jojo", "Émile et Gégé", "Sakura & Kenji", "Mikey & John", "Elizabeth & Charles"]
    rfid_uids = ["1234567890", "0987654321", "1122334455", "5566778899", "6677889900"]
    max_times = [3600, 3600, 7200, 5400, 3600]
    creation_timestamps = [
        datetime(2024, 5, 20, 12, 34, 56).timestamp(),  # a few weeks ago
        datetime(2024, 5, 21, 12, 34, 56).timestamp(),  # a few weeks ago
        (datetime.now() - timedelta(days=5)).timestamp(),  # 5 days ago
        (datetime.now() - timedelta(days=30)).timestamp(),  # 1 month ago
        (datetime.now() - timedelta(days=90)).timestamp()  # 3 months ago
    ]
    start_timestamps = [
        datetime(2024, 5, 21, 12, 40, 20).timestamp(),
        datetime(2024, 5, 22, 12, 55, 0).timestamp(),
        (datetime.now() - timedelta(days=4)).timestamp(),
        (datetime.now() - timedelta(days=29)).timestamp(),
        (datetime.now() - timedelta(days=89)).timestamp()
    ]
    completed_cubeboxes_list = [
        [
            cube_game.CubeboxStatus(cube_id=1, start_timestamp=0, win_timestamp=1000),
            cube_game.CubeboxStatus(cube_id=2, start_timestamp=1000, win_timestamp=2000),
        ],
        [
            cube_game.CubeboxStatus(cube_id=3, start_timestamp=0, win_timestamp=1000),
            cube_game.CubeboxStatus(cube_id=4, start_timestamp=1000, win_timestamp=2000),
            cube_game.CubeboxStatus(cube_id=5, start_timestamp=2000, win_timestamp=3000),
        ],
        [
            cube_game.CubeboxStatus(cube_id=6, start_timestamp=0, win_timestamp=1000),
            cube_game.CubeboxStatus(cube_id=7, start_timestamp=1000, win_timestamp=2000),
        ],
        [
            cube_game.CubeboxStatus(cube_id=8, start_timestamp=0, win_timestamp=1000),
            cube_game.CubeboxStatus(cube_id=9, start_timestamp=1000, win_timestamp=2000),
            cube_game.CubeboxStatus(cube_id=10, start_timestamp=2000, win_timestamp=3000),
        ],
        [
            cube_game.CubeboxStatus(cube_id=11, start_timestamp=0, win_timestamp=1000),
            cube_game.CubeboxStatus(cube_id=12, start_timestamp=1000, win_timestamp=2000),
        ]
    ]
    trophies_names_list = [
        [
            "Trophy1", "Trophy2"
        ],
        [
            "Trophy3", "Trophy4", "Trophy5"
        ],
        [
            "Trophy6", "Trophy7"
        ],
        [
            "Trophy8", "Trophy9", "Trophy10"
        ],
        [
            "Trophy11", "Trophy12"
        ]
    ]

    # Loop to add teams
    for name, custom_name, rfid_uid, max_time, creation_timestamp, start_timestamp, completed_cubeboxes, trophies_names in zip(
            names, custom_names, rfid_uids, max_times, creation_timestamps, start_timestamps, completed_cubeboxes_list,
            trophies_names_list
    ):
        completed_cubeboxes = cube_game.CompletedCubeboxStatusList(completed_cubeboxes)
        teams.add_team(cube_game.CubeTeamStatus(
            name=name,
            custom_name=custom_name,
            rfid_uid=rfid_uid,
            max_time_sec=max_time,
            creation_timestamp=creation_timestamp,
            start_timestamp=start_timestamp,
            completed_cubeboxes=completed_cubeboxes,
            trophies_names=trophies_names
        ))

    return teams


def generate_sample_teams_json_database():
    teams = generate_sample_teams()
    if teams.save_to_json_file(TEAMS_JSON_DATABASE_FILEPATH):
        print("Sample teams saves generated:")
        print(teams.to_string())


def generate_sample_teams_sqlite_database():
    """same as the json database, but in sqlite"""
    teams = generate_sample_teams()
    from thecubeivazio.cube_database import delete_database
    delete_database(TEAMS_SQLITE_DATABASE_FILEPATH)
    if teams.save_to_sqlite_database(TEAMS_SQLITE_DATABASE_FILEPATH):
        print("Sample teams sqlite database generated:")
        print(teams.to_string())


def display_teams_sqlite_database():
    teams = cubedb.load_all_teams()
    print(teams.to_string())
    print(f"nb teams: {len(teams)}")


def run_prompt():
    import atexit
    fd = CubeServerFrontdeskWithPrompt()
    atexit.register(fd.stop)
    fd.run()

def test_send_config():
    from thecubeivazio.cubeserver_cubebox import CubeServerCubebox
    from thecubeivazio.cubeserver_cubemaster import CubeServerMaster
    import traceback

    fd = CubeServerFrontdesk()
    cm = CubeServerMaster()
    cb = CubeServerCubebox("CubeBox1")

    fd.run()
    cm.run()
    cb.run()
    cb.rfid.disable()
    fd.log.setLevel(logging.ERROR)
    fd.net.log.setLevel(logging.ERROR)
    cm.log.setLevel(logging.ERROR)
    cm.net.log.setLevel(logging.ERROR)
    cb.log.setLevel(logging.ERROR)
    cb.net.log.setLevel(logging.ERROR)
    value = f"test{time.time()}"
    fd.config.set_field("test", value)
    nodenames = [cm.net.node_name, cb.net.node_name]
    assert fd.config.get_field("test") == value
    assert fd.send_config_message_to_all(fd.config, nodenames)
    assert cm.config.get_field("test") == value
    assert cb.config.get_field("test") == value
    print(f"fd.config.get_field('test')={fd.config.get_field('test')}")
    print(f"cm.config.get_field('test')={cm.config.get_field('test')}")
    print(f"cb.config.get_field('test')={cb.config.get_field('test')}")
    print("test_send_config: OK")
    fd.stop()
    cm.stop()
    cb.stop()
    exit(0)


if __name__ == "__main__":
    test_send_config()
    # generate_sample_teams_json_database()
    generate_sample_teams_sqlite_database()
    display_teams_sqlite_database()
    exit(0)
    run_prompt()
