"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""
import cube_logger
import cube_rfid
import cube_networking as cubenet
import cube_messages as cm


class CubeBox:
    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(node_name)
        self.net = cubenet.CubeNetworking(node_name=node_name)
        self.rfid = cube_rfid.CubeRfidListener()

    def run(self):
        self.net.run()
        self.rfid.run()
        while True:
            self.handle_networking()
            self.handle_rfid()
            self.handle_button()

    def handle_networking(self):
        """check the incoming messages and handle them"""
        for message in self.net.get_incoming_msg_queue():
            if message.msgtype == cm.CubeMsgType.VERSION_REQUEST:
                self.net.add_to_outgoing_msg_queue(cm.CubeMsgVersionReply(self.net.node_name))


if __name__ == "__main__":
    box = CubeBox("CubeBox1")
    box.run()