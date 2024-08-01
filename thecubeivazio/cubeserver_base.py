import thecubeivazio.cube_game as cube_game
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_utils as cube_utils
from thecubeivazio import cube_config
from thecubeivazio import cube_database as cubedb
from thecubeivazio.cube_common_defines import *

class CubeServerBase:
    log: cube_logger.CubeLogger
    net: cubenet.CubeNetworking
    game_status: cube_game.CubeGameStatus

    def __init__(self):
        pass

    @property
    def teams(self) -> cube_game.CubeTeamsStatusList:
        return self.game_status.teams

    @teams.setter
    def teams(self, value: cube_game.CubeTeamsStatusList):
        self.game_status.teams = value

    @property
    def cubeboxes(self) -> cube_game.CubeboxesStatusList:
        return self.game_status.cubeboxes

    @cubeboxes.setter
    def cubeboxes(self, value: cube_game.CubeboxesStatusList):
        self.game_status.cubeboxes = value

    @cubetry
    def send_full_command(self, full_command:str) -> cubenet.SendReport:
        """Send a full command to a node. Returns True if the command was sent, False if not."""
        self.log.info(f"Sending full command: {full_command}")
        msg = cm.CubeMsgCommand(self.net.node_name, full_command=full_command)
        self.log.critical(f"words={msg.words}")
        destination_node = msg.target
        if destination_node not in cubeid.ALL_NODENAMES:
            self.log.error(f"Invalid destination node: {destination_node}")
            return cubenet.SendReport(sent_ok=False, raw_info=f"Invalid destination node: {destination_node}")
        report = self.net.send_msg_to(msg, destination_node, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the full command : {full_command}")
            report._raw_info = f"Failed to send the command : '{full_command}'"
            return report
        if not report.ack_ok:
            self.log.error(f"Node {destination_node} did not acknowledge the full command : '{full_command}'")
            report._raw_info = f"Node {destination_node} did not acknowledge the full command : '{full_command}'"
            return report
        self.log.success(f"Node {destination_node} acknowledged the full command : {full_command}")
        return report

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
            assert self._handle_reply_cubebox_status(reply_msg)
            rcs_msg = cm.CubeMsgReplyCubeboxStatus(copy_msg=reply_msg)
            reply_cubebox_id = rcs_msg.cubebox.cube_id
            if reply_cubebox_id != cubebox_id:
                self.log.error(f"Received cubebox status reply for cubebox {reply_cubebox_id} instead of {cubebox_id}")
                return False
            self.log.success(f"Received cubebox status reply for cubebox {cubebox_id}")
            return True
        # no timeout? just return True
        return True

    @cubetry
    def _handle_reply_cubebox_status(self, message: cm.CubeMessage) -> bool:
        self.log.info(f"Received reply cubebox status message from {message.sender}")
        acsr_msg = cm.CubeMsgReplyCubeboxStatus(copy_msg=message)
        new_cubebox = acsr_msg.cubebox
        assert new_cubebox, "_handle_reply_cubebox_status: new_cubebox is None"
        assert self.cubeboxes.update_from_cubebox(new_cubebox), "_handle_reply_cubebox_status: update_cubebox failed"
        self.net.acknowledge_this_message(message, info=cm.CubeAckInfos.OK)
        return True

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

    def _handle_reply_all_cubeboxes_status_hashes(self, message: cm.CubeMessage):
        self.log.info(f"Received reply all cubeboxes status hashes message from {message.sender}")
        self.log.error("_handle_reply_all_cubeboxes_status_hashes: not implemented")

    def _handle_reply_all_teams_status_hashes(self, message: cm.CubeMessage):
        self.log.info(f"Received reply all teams status hashes message from {message.sender}")
        self.log.error("_handle_reply_all_teams_status_hashes: not implemented")

    def _handle_cubemaster_cubebox_status_message(self, message: cm.CubeMessage):
        self.log.info(f"Received cubemaster cubebox status message from {message.sender}")
        self.log.error("_handle_cubemaster_cubebox_status_message: not implemented")