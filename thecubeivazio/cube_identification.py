"""Handles everything related to identifying each server (network node) involved in the game:
- front desk
- central cube server
- all cubebox servers
"""

from typing import Optional, Dict
from thecubeivazio import cube_utils
from thecubeivazio.cube_common_defines import *

CUBEFRONTDESK_NODENAME = "CubeFrontdesk"
CUBEMASTER_NODENAME = "CubeMaster"
CUBEBOX_NODENAME_PREFIX = "CubeBox"
EVERYONE_NODENAME = "CubeEveryone"

NB_CUBEBOXES = 12
FIRST_CUBEBOX_INDEX = 1
CUBEBOX_IDS = tuple(range(FIRST_CUBEBOX_INDEX, FIRST_CUBEBOX_INDEX + NB_CUBEBOXES))
CUBEBOX_NODENAMES = tuple(f"{CUBEBOX_NODENAME_PREFIX}{i}" for i in CUBEBOX_IDS)
ALL_NODENAMES = (CUBEFRONTDESK_NODENAME, CUBEMASTER_NODENAME) + CUBEBOX_NODENAMES


@cubetry
def is_valid_node_name(name: str) -> bool:
    """Checks if the node name is one of the valid node names."""
    if not isinstance(name, str):
        return False
    return name in [CUBEFRONTDESK_NODENAME, CUBEMASTER_NODENAME] or name.startswith(CUBEBOX_NODENAME_PREFIX)


def is_valid_ip(ip: str) -> bool:
    """Checks if the IP address is a string of 4 numbers separated by dots, each number being between 0 and 255."""
    return ip.count(".") == 3 and all([0 <= int(num) <= 255 for num in ip.split(".")])


def node_name_to_cubebox_index(name: str) -> Optional[int]:
    if name.startswith(CUBEBOX_NODENAME_PREFIX):
        try:
            return int(name[len(CUBEBOX_NODENAME_PREFIX):])
        except ValueError:
            return None
    else:
        return None


def cubebox_index_to_node_name(index: int) -> str:
    return f"{CUBEBOX_NODENAME_PREFIX}{index}"


def hostname_to_valid_cubebox_name(username: str=None) -> Optional[str]:
    """checks the system username. if there's a number in it,
    returns the corresponding cubebox name, else returns CubeEveryone"""
    try:
        if username is None:
            username = cube_utils.get_system_hostname()
        # get the number in the username
        number_str = "".join([c for c in username if c.isdigit()])
        if int(number_str) in CUBEBOX_IDS:
            return f"{CUBEBOX_NODENAME_PREFIX}{number_str}"
    except Exception as e:
        print(f"Error while converting system username to cubebox name: {e}")
        return None


class NodeInfo:
    """Container used to identify a node.
    Attributes:
    - name: the name of the node
    - ip: the IP address of the node
    - last_msg_timestamp: the timestamp of the last message received from the node
    """

    def __init__(self, name: NodeName, ip: str, last_msg_timestamp:Timestamp=None):
        self.name = name
        self.ip = ip
        self.last_msg_timestamp = last_msg_timestamp

    def is_valid(self) -> bool:
        return is_valid_node_name(self.name) and is_valid_ip(self.ip)

    def is_cubebox(self) -> bool:
        return self.name.startswith(CUBEBOX_NODENAME_PREFIX)

    def to_string(self) -> str:
        return f"{self.name}: name={self.name}, ip={self.ip}"


class NodesList(Dict[str, NodeInfo]):
    def __init__(self):
        super().__init__()
        self[CUBEFRONTDESK_NODENAME] = NodeInfo(CUBEFRONTDESK_NODENAME, "")
        self[CUBEMASTER_NODENAME] = NodeInfo(CUBEMASTER_NODENAME, "")
        for i in CUBEBOX_IDS:
            self[f"{CUBEBOX_NODENAME_PREFIX}{i}"] = NodeInfo(f"{CUBEBOX_NODENAME_PREFIX}{i}", "")

    def __eq__(self, other: 'NodesList'):
        return self.hash == other.hash

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "\n".join([node.to_string() for node in self.values()])

    @property
    def hash(self) -> Hash:
        import hashlib
        return hashlib.sha256(str(self).encode()).hexdigest()

    @property
    def frontdesk(self) -> NodeInfo:
        return self[CUBEFRONTDESK_NODENAME]

    @property
    def cubemaster(self) -> NodeInfo:
        return self[CUBEMASTER_NODENAME]

    @property
    def cubeboxes(self) -> list[NodeInfo]:
        return [self[f"{CUBEBOX_NODENAME_PREFIX}{i}"] for i in CUBEBOX_IDS]

    def is_complete(self) -> bool:
        return all([is_valid_ip(node.ip) for node in [self.frontdesk, self.cubemaster] + self.cubeboxes])

    def set_node_ip_for_node_name(self, node_name:str, ip:str):
        if node_name == CUBEFRONTDESK_NODENAME:
            self.frontdesk.ip = ip
        elif node_name == CUBEMASTER_NODENAME:
            self.cubemaster.ip = ip
        elif node_name.startswith(CUBEBOX_NODENAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(node_name)
            if cubebox_index is not None:
                self.cubeboxes[cubebox_index - 1].ip = ip

    def get_node_ip_from_node_name(self, node_name:str) -> Optional[str]:
        if node_name == CUBEFRONTDESK_NODENAME:
            return self.frontdesk.ip
        elif node_name == CUBEMASTER_NODENAME:
            return self.cubemaster.ip
        elif node_name.startswith(CUBEBOX_NODENAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(node_name)
            if cubebox_index is not None:
                return self.cubeboxes[cubebox_index - 1].ip
        return None

    def set_last_msg_timestamp_for_node_name(self, sender:NodeName, timestamp:Timestamp):
        if sender == CUBEFRONTDESK_NODENAME:
            self.frontdesk.last_msg_timestamp = timestamp
        elif sender == CUBEMASTER_NODENAME:
            self.cubemaster.last_msg_timestamp = timestamp
        elif sender.startswith(CUBEBOX_NODENAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(sender)
            if cubebox_index is not None:
                self.cubeboxes[cubebox_index - 1].last_msg_timestamp = timestamp

    def get_last_msg_timestamp_from_node_name(self, sender:NodeName) -> Optional[Timestamp]:
        if sender == CUBEFRONTDESK_NODENAME:
            return self.frontdesk.last_msg_timestamp
        elif sender == CUBEMASTER_NODENAME:
            return self.cubemaster.last_msg_timestamp
        elif sender.startswith(CUBEBOX_NODENAME_PREFIX):
            cubebox_index = node_name_to_cubebox_index(sender)
            if cubebox_index is not None:
                return self.cubeboxes[cubebox_index - 1].last_msg_timestamp
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

