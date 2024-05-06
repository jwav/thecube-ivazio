"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""
import cube_logger
import cube_networking as cbnet
import cube_rfid


class CubeBox:
    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(node_name)
        self.net = cbnet.CubeNetworking(node_name=node_name)
        self.rfid = cube_rfid.CubeRfidListener()

    def start(self):
        self.net.start()
        self.rfid.start()


if __name__ == "__main__":
    box = CubeBox("CubeBox1")
    box.start()