"""Handles everything related to identifying each server (network node) involved in the game:
- front desk
- central cube server
- all cubebox servers
"""

from typing import Union, Optional

NB_CUBEBOXES = 12
FRONTDESK_NAME = "FrontDesk"
CUBESERVER_NAME = "CubeServer"
CUBEBOX_NAME_PREFIX = "CubeBox"

IDENTIFICATION_MESSAGE = "whospartofthecube?"
CUBESERVER_IDENTIFICATION_MESSAGE = "imthecubeserver"
FRONTDESK_IDENTIFICATION_MESSAGE = "imthecubefrontdesk"
CUBEBOX_IDENTIFICATION_PREFIX = "imacubebox:"


def get_node_name_from_response(response: str) -> str:
    if not response.startswith(CUBEBOX_IDENTIFICATION_PREFIX):
        return ""
    else:
        return response[len(CUBEBOX_IDENTIFICATION_PREFIX):]


def make_response_from_node_name(name: str) -> str:
    if name == FRONTDESK_NAME:
        return FRONTDESK_IDENTIFICATION_MESSAGE
    elif name == CUBESERVER_NAME:
        return CUBESERVER_IDENTIFICATION_MESSAGE
    elif name.startswith(CUBEBOX_NAME_PREFIX):
        return f"{CUBEBOX_IDENTIFICATION_PREFIX}{name}"


def is_valid_node_name(name: str) -> bool:
    return name in [FRONTDESK_NAME, CUBESERVER_NAME] or name.startswith(CUBEBOX_NAME_PREFIX)


def is_valid_ip(ip: str) -> bool:
    return ip.count(".") == 3 and all([0 <= int(num) <= 255 for num in ip.split(".")])


def node_name_to_cubebox_index(name: str) -> Optional[int]:
    if name.startswith(CUBEBOX_NAME_PREFIX):
        try:
            return int(name[len(CUBEBOX_NAME_PREFIX):])
        except ValueError:
            return None
    else:
        return None


def cubebox_index_to_node_name(index: int) -> str:
    return f"{CUBEBOX_NAME_PREFIX}{index}"


class NodeInfo:
    """Container used to identify a node"""

    def __init__(self, name: str, ip: str):
        self.name = name
        self.ip = ip

    def is_valid(self) -> bool:
        return is_valid_node_name(self.name) and is_valid_ip(self.ip)

    def is_cubebox(self) -> bool:
        return self.name.startswith(CUBEBOX_NAME_PREFIX)

    def to_string(self) -> str:
        return f"{self.name}: name={self.name}, ip={self.ip}"


class NodesList:
    def __init__(self):
        self.frontDesk = NodeInfo(FRONTDESK_NAME, "")
        self.cubeServer = NodeInfo(CUBESERVER_NAME, "")
        self.cubeBoxes = [NodeInfo(f"{CUBEBOX_NAME_PREFIX}{i}", "") for i in range(1, NB_CUBEBOXES + 1)]

    def is_complete(self) -> bool:
        return all([is_valid_ip(node.ip) for node in [self.frontDesk, self.cubeServer] + self.cubeBoxes])

    def to_string(self):
        return f"FrontDesk: name={self.frontDesk.name}, ip={self.frontDesk.ip}\n" + \
            f"CubeServer: name={self.cubeServer.name}, ip={self.cubeServer.ip}\n" + \
            "\n".join([f"{cubebox.name}: name={cubebox.name}, ip={cubebox.ip}" for cubebox in self.cubeBoxes])

    def set_node_ip_from_node_name(self, node_name:str, ip:str):
        if node_name == FRONTDESK_NAME:
            self.frontDesk.ip = ip
        elif node_name == CUBESERVER_NAME:
            self.cubeServer.ip = ip
        elif node_name.startswith(CUBEBOX_NAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(node_name)
            if cubebox_index is not None:
                self.cubeBoxes[cubebox_index - 1].ip = ip


if __name__ == "__main__":
    nodes_list = NodesList()
    # display the list of all nodes, names and ips
    print(nodes_list.to_string())
