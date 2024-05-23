"""Handles everything related to identifying each server (network node) involved in the game:
- front desk
- central cube server
- all cubebox servers
"""

from typing import Optional
from thecubeivazio import cube_utils

NB_CUBEBOXES = 12
FIRST_CUBEBOX_INDEX = 1
CUBEBOX_IDS = range(FIRST_CUBEBOX_INDEX, FIRST_CUBEBOX_INDEX + NB_CUBEBOXES)
CUBEFRONTDESK_NAME = "CubeFrontdesk"
CUBEMASTER_NAME = "CubeMaster"
CUBEBOX_NAME_PREFIX = "CubeBox"
EVERYONE_NAME = "CubeEveryone"


def is_valid_node_name(name: str) -> bool:
    return name in [CUBEFRONTDESK_NAME, CUBEMASTER_NAME] or name.startswith(CUBEBOX_NAME_PREFIX)


def is_valid_ip(ip: str) -> bool:
    """Checks if the IP address is a string of 4 numbers separated by dots, each number being between 0 and 255."""
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


def hostname_to_valid_cubebox_name(username: str=None) -> Optional[str]:
    """checks the system username. if there's a number in it,
    returns the corresponding cubebox name, else returns CubeEveryone"""
    try:
        if username is None:
            username = cube_utils.get_system_hostname()
        # get the number in the username
        number_str = "".join([c for c in username if c.isdigit()])
        if int(number_str) in CUBEBOX_IDS:
            return f"{CUBEBOX_NAME_PREFIX}{number_str}"
    except Exception as e:
        print(f"Error while converting system username to cubebox name: {e}")
        return None


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
        self.frontDesk = NodeInfo(CUBEFRONTDESK_NAME, "")
        self.cubeServer = NodeInfo(CUBEMASTER_NAME, "")
        self.cubeBoxes = [NodeInfo(f"{CUBEBOX_NAME_PREFIX}{i}", "") for i in range(1, NB_CUBEBOXES + 1)]

    def is_complete(self) -> bool:
        return all([is_valid_ip(node.ip) for node in [self.frontDesk, self.cubeServer] + self.cubeBoxes])

    def to_string(self):
        return f"FrontDesk: name={self.frontDesk.name}, ip={self.frontDesk.ip}\n" + \
            f"CubeMaster: name={self.cubeServer.name}, ip={self.cubeServer.ip}\n" + \
            "\n".join([f"{cubebox.name}: name={cubebox.name}, ip={cubebox.ip}" for cubebox in self.cubeBoxes])

    def set_node_ip_from_node_name(self, node_name:str, ip:str):
        if node_name == CUBEFRONTDESK_NAME:
            self.frontDesk.ip = ip
        elif node_name == CUBEMASTER_NAME:
            self.cubeServer.ip = ip
        elif node_name.startswith(CUBEBOX_NAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(node_name)
            if cubebox_index is not None:
                self.cubeBoxes[cubebox_index - 1].ip = ip

    def get_node_ip_from_node_name(self, node_name:str) -> Optional[str]:
        if node_name == CUBEFRONTDESK_NAME:
            return self.frontDesk.ip
        elif node_name == CUBEMASTER_NAME:
            return self.cubeServer.ip
        elif node_name.startswith(CUBEBOX_NAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(node_name)
            if cubebox_index is not None:
                return self.cubeBoxes[cubebox_index - 1].ip
        return None


if __name__ == "__main__":
    print([x for x in CUBEBOX_IDS])
    nodes_list = NodesList()
    # display the list of all nodes, names and ips
    print(nodes_list.to_string())
    print("cubebox username test:")
    print(f"username=cubebox1 -> {hostname_to_valid_cubebox_name('cubebox1')}")
    print(f"username=cubebox2 -> {hostname_to_valid_cubebox_name('cubebox2')}")
    print(f"username=cubebox100 -> {hostname_to_valid_cubebox_name('cubebox100')}")
    print(f"username=cubebox -> {hostname_to_valid_cubebox_name('cubebox')}")
    print(f"username=box1 -> {hostname_to_valid_cubebox_name('box1')}")

