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

    def __init__(self):
        pass

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