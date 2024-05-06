"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""

import cube_networking as cbnet


class CubeBox:
    def __init__(self, node_name: str):
        self.net = cbnet.CubeNetworking(node_name=node_name)
        raise NotImplementedError


if __name__ == "__main__":
    raise NotImplementedError
