"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""
import json
import time
from typing import Optional, Dict, Type
import enum


import thecubeivazio.cube_game as cube_game
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid

from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_logger import CubeLogger


class CubeMsgTypes(enum.Enum):
    """Enumeration of the different types of messages that can be sent."""
    TEST = "TEST"

    # sent from a node to another node to acknowledge that the message has been received and handled.
    # can include an info, see the MsgAck class for standard values for `info`
    HEARTBEAT = "HEARTBEAT"
    ACK = "ACK"
    WHO_IS = "WHO_IS"

    REQUEST_VISION = "REQUEST_VISION"
    REQUEST_CUBEMASTER_STATUS = "REQUEST_CUBEMASTER_STATUS"
    REQUEST_CUBEMASTER_STATUS_HASH = "REQUEST_CUBEMASTER_STATUS_HASH"
    REQUEST_CUBEMASTER_CUBEBOX_STATUS = "REQUEST_CUBEMASTER_CUBEBOX_STATUS"
    REQUEST_ALL_CUBEBOXES_STATUSES = "REQUEST_ALL_CUBEBOXES_STATUS"
    REQUEST_CUBEBOX_STATUS = "REQUEST_CUBEBOX_STATUS"
    REQUEST_TEAM_STATUS = "REQUEST_TEAM_STATUS"
    REQUEST_ALL_TEAMS_STATUSES = "REQUEST_ALL_TEAMS_STATUS"
    REQUEST_ALL_TEAMS_STATUS_HASHES = "REQUEST_ALL_TEAMS_STATUS_HASHES"
    REQUEST_ALL_CUBEBOXES_STATUS_HASHES = "REQUEST_ALL_CUBEBOXES_STATUS_HASHES"

    REPLY_VERSION = "REPLY_VERSION"
    REPLY_CUBEMASTER_STATUS = "REPLY_CUBEMASTER_STATUS"
    REPLY_CUBEMASTER_STATUS_HASH = "REPLY_CUBEMASTER_STATUS_HASH"
    REPLY_CUBEBOX_STATUS = "REPLY_CUBEMASTER_CUBEBOX_STATUS"
    REPLY_ALL_CUBEBOXES_STATUSES = "REPLY_ALL_CUBEBOXES_STATUSES"
    REPLY_TEAM_STATUS = "REPLY_TEAM_STATUS"
    REPLY_ALL_TEAMS_STATUSES = "REPLY_ALL_TEAMS_STATUSES"
    REPLY_ALL_TEAMS_STATUS_HASHES = "REPLY_ALL_TEAMS_STATUS_HASHES"
    REPLY_ALL_CUBEBOXES_STATUS_HASHES = "REPLY_ALL_CUBEBOXES_STATUS_HASHES"

    ORDER_CUBEBOX_TO_WAIT_FOR_RESET = "ORDER_CUBEBOX_TO_WAIT_FOR_RESET"
    ORDER_CUBEBOX_TO_RESET = "ORDER_CUBEBOX_TO_RESET"

    # Messages sent by the CubeBox besides status messages
    CUBEBOX_RFID_READ = "CUBEBOX_RFID_READ"
    CUBEBOX_BUTTON_PRESS = "CUBEBOX_BUTTON_PRESS"

    # Messages sent by the CubeMaster besides status messages

    # Messages sent by the Frontdesk
    FRONTDESK_NEW_TEAM = "FRONTDESK_NEW_TEAM"
    FRONTDESK_REMOVE_TEAM = "FRONTDESK_REMOVE_TEAM"


    # unneeded by way of empirical evidence, but hey, i needed to do it for CubeMsgReplies and I guess i can't hurt
    def __eq__(self, other):
        """This is needed to compare a CubeMsgTypes with a str."""
        return str(self) == str(other)


class CubeAckInfos(enum.Enum):
    """Enumeration of the different types of replies that can be sent."""
    NONE = "NONE"
    OK = "OK"
    ERROR = "ERROR"
    FAILED = "FAILED"
    DENIED = "DENIED"
    INVALID = "INVALID"
    OCCUPIED = "OCCUPIED"

    def __str__(self):
        return self.value

    def __eq__(self, other):
        """This is needed to compare a CubeMsgReplies with a string."""
        return str(self) == str(other)


class CubeMessage:
    """Base class for all messages."""
    SEPARATOR = "|"
    PREFIX = "CUBEMSG"

    def __init__(self, msgtype: CubeMsgTypes = None, sender: str = None, copy_msg: 'CubeMessage' = None, **kwargs):
        if copy_msg is not None:
            self.build_from_message(copy_msg)
            return
        self.msgtype = msgtype
        self.sender = sender
        self.sender_ip = None
        self.kwargs = kwargs
        # must be manually set to False if no acknowledgement is required
        self.require_ack = True

    def __eq__(self, other):
        return self.to_string() == other.to_string()

    @property
    def hash(self):
        """Returns an alphanumeric hash of the message, using SHA256"""
        import hashlib
        return hashlib.sha256(self.to_string().encode()).hexdigest()

    def copy(self):
        ret = CubeMessage(self.msgtype, self.sender, **self.kwargs)
        ret.require_ack = self.require_ack
        return ret

    def is_valid(self):
        return all([isinstance(self.sender, str), isinstance(self.msgtype, CubeMsgTypes),
                    all([isinstance(k, str) for k in self.kwargs.keys()])])

    def to_string(self):
        sep = self.SEPARATOR
        return f"{self.PREFIX}{sep}sender={self.sender}{sep}msgtype={self.msgtype.name}{sep}{sep.join([f'{k}={v}' for k, v in self.kwargs.items()])}"

    def to_bytes(self):
        return self.to_string().encode()

    # NOTE: DO NOT USE THIS METHOD
    # NOTE: uh, why?
    @classmethod
    def make_from_message(cls, msg: 'CubeMessage'):
        # print("make_from_message : cls=", cls)
        ret = cls()
        ret.build_from_message(msg)
        return ret

    def build_from_message(self, msg: 'CubeMessage'):
        self.msgtype = msg.msgtype
        self.sender = msg.sender
        self.kwargs = msg.kwargs
        self.sender_ip = msg.sender_ip
        self.require_ack = msg.require_ack

    def build_from_bytes(self, msg_bytes: bytes):
        self.build_from_string(msg_bytes.decode())

    @classmethod
    def make_from_string(cls, msg_str: str):
        ret = cls()
        ret.build_from_string(msg_str)
        return ret

    def build_from_string(self, msg_str: str):
        sep = CubeMessage.SEPARATOR
        if not msg_str.startswith(CubeMessage.PREFIX):
            return None
        parts = msg_str.split(sep)
        # print(f"build_from_string() : parts={parts}")
        if len(parts) < 3:
            return None
        sender = None
        msgtype = None
        kwargs = {}
        # print(parts)
        # print(parts[1:])
        for part in parts[1:]:
            try:
                key, value = part.split("=")
            except ValueError:
                continue
            if key == "sender":
                sender = value
            elif key == "msgtype":
                msgtype = value
            else:
                kwargs[key] = value
        if not all([sender, msgtype]):
            return None
        self.build_from_message(CubeMessage(CubeMsgTypes[msgtype], sender, **kwargs))

    def is_ack_of(self, other: 'CubeMessage'):
        """Returns True if this message is an acknowledgement of the other message."""
        return self.msgtype == CubeMsgTypes.ACK and self.kwargs.get("acked_hash") == other.hash

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()


# messages sent by the Frontdesk besides status messages

class CubeMsgFrontdeskNewTeam(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster when a new team is registered."""

    def __init__(self, sender=None, team: cube_game.CubeTeamStatus = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.FRONTDESK_NEW_TEAM, sender, name=team.name, rfid_uid=team.rfid_uid,
                             max_time_sec=team.max_time_sec)
        self.require_ack = True

    @property
    def team(self) -> Optional[cube_game.CubeTeamStatus]:
        name = self.kwargs.get("name", None)
        rfid_uid = self.kwargs.get("rfid_uid", None)
        max_time_sec = float(self.kwargs.get("max_time_sec", None))
        if not all([name, rfid_uid, max_time_sec]):
            return None
        return cube_game.CubeTeamStatus(
            name=name, rfid_uid=rfid_uid, max_time_sec=max_time_sec)


# TODO: handle in cubemaster
class CubeMsgFrontdeskRemoveTeam(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster when a team is removed."""

    def __init__(self, sender=None, team_name=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.FRONTDESK_REMOVE_TEAM, sender, team_name=team_name)
        self.require_ack = True

    @property
    def team_name(self) -> str:
        return str(self.kwargs.get("team_name"))


# messages sent by the CubeBox besides status messages

class CubeMsgButtonPress(CubeMessage):
    """Sent from the CubeBox to the CubeMaster when the button is pressed.
    The timestamps are those calculated by the CubeBox."""

    def __init__(self, sender=None, start_timestamp=None, press_timestamp=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.CUBEBOX_BUTTON_PRESS, sender, start_timestamp=start_timestamp,
                             press_timestamp=press_timestamp)
        self.require_ack = True

    @property
    def start_timestamp(self) -> Optional[float]:
        try:
            return float(self.kwargs.get("start_timestamp"))
        except ValueError:
            return None

    @property
    def press_timestamp(self) -> Optional[float]:
        try:
            return float(self.kwargs.get("press_timestamp"))
        except ValueError:
            return None

    @property
    def elapsed_time(self) -> Optional[float]:
        try:
            return self.press_timestamp - self.start_timestamp
        except TypeError:
            return None

    def has_valid_times(self):
        """Returns True if the timestamps are valid (not None and press > start)"""
        try:
            return self.press_timestamp > self.start_timestamp
        except TypeError:
            return False

    @property
    def cube_id(self) -> Optional[CubeId]:
        return cubeid.node_name_to_cubebox_index(self.sender)


class CubeMsgRfidRead(CubeMessage):
    """Sent from the CubeBox to the CubeMaster when an RFID tag is read."""

    def __init__(self, sender=None, uid=None, timestamp=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.CUBEBOX_RFID_READ, sender, uid=uid, timestamp=timestamp)
        self.require_ack = True

    @property
    def uid(self) -> str:
        return str(self.kwargs.get("uid"))

    @property
    def timestamp(self) -> float:
        return float(self.kwargs.get("timestamp"))


# version request & reply

class CubeMsgRequestVersion(CubeMessage):
    """Sent from a node to another node to ask for its version."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_VISION, sender)
        self.require_ack = False


class CubeMsgReplyVersion(CubeMessage):
    """Sent from a node to another node in response to a VERSION_REQUEST message."""

    def __init__(self, sender):
        from cube_utils import get_git_branch_date
        super().__init__(CubeMsgTypes.REPLY_VERSION, sender, version=get_git_branch_date())

    @property
    def version(self) -> str:
        return self.kwargs.get("version")


# cubemaster status request & reply

class CubeMsgRequestCubemasterStatus(CubeMessage):
    """Sent from a node to the CubeMaster to ask for its status."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_CUBEMASTER_STATUS, sender)
        self.require_ack = False

# TODO
class CubeMsgReplyCubemasterStatus(CubeMessage):
    """Sent from the CubeMaster to a node in response to a REQUEST_CUBEMASTER_STATUS message."""

    def __init__(self, sender=None, status: cube_game.CubeGameStatus = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_CUBEMASTER_STATUS, sender)
            if status:
                self.kwargs["cubemaster_status"] = status.to_json()
        self.require_ack = False

    @property
    def cubemaster_status(self) -> cube_game.CubeGameStatus:
        return cube_game.CubeGameStatus.make_from_json(self.kwargs.get("cubemaster_status"))

class CubeMsgRequestCubeMasterStatusHash(CubeMessage):
    """Sent from a node to the CubeMaster to ask for its status hash."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_CUBEMASTER_STATUS_HASH, sender)
        self.require_ack = False


# noinspection PyShadowingBuiltins
class CubeMsgReplyCubeMasterStatusHash(CubeMessage):
    """Sent from the CubeMaster to a node in response to a REQUEST_CUBEMASTER_STATUS_HASH message."""

    def __init__(self, sender=None, hash: Hash = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_CUBEMASTER_STATUS_HASH, sender, hash=hash)
        self.require_ack = False

    @property
    def hash(self) -> str:
        return str(self.kwargs.get("hash"))


# cubebox status request & reply

class CubeMsgRequestCubeboxStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of a cubebox."""

    def __init__(self, sender=None, cube_id=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REQUEST_CUBEMASTER_CUBEBOX_STATUS, sender, cube_id=cube_id)
        self.require_ack = True

    @property
    def cube_id(self) -> int:
        return int(self.kwargs.get("cube_id"))

# TODO: testme

class CubeMsgReplyCubeboxStatus(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_CUBEBOX_STATUS message."""

    def __init__(self, sender=None, status: cube_game.CubeboxStatus = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_CUBEBOX_STATUS, sender)
            if status:
                self.kwargs["cubebox_status"] = status.to_json()

        self.require_ack = False

    @property
    def cubebox(self) -> cube_game.CubeboxStatus:
        return cube_game.CubeboxStatus.make_from_json(self.kwargs.get("cubebox_status"))


class CubeMsgRequestAllCubeboxesStatuses(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of all cubeboxes."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUSES, sender)
        self.require_ack = False



class CubeMsgReplyAllCubeboxesStatuses(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_ALL_CUBEBOXES_STATUSES message."""

    def __init__(self, sender=None, statuses: cube_game.CubeboxesStatusList = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_ALL_CUBEBOXES_STATUSES, sender, statuses=statuses)
            if statuses:
                self.kwargs[cube_game.CubeboxesStatusList.JSON_ROOT_OBJECT_NAME] = statuses.to_json()
                # print(f"CubeMsgReplyAllCubeboxesStatuses : self.kwargs={self.kwargs}")
        self.require_ack = False

    @property
    def cubeboxes_statuses(self) -> Optional[cube_game.CubeboxesStatusList]:
        # parse self.kwargs.get("statuses") to a dict
        try:
            json_statuses = self.kwargs.get(cube_game.CubeboxesStatusList.JSON_ROOT_OBJECT_NAME)
            # print(f"json_statuses={json_statuses}")
            # print(f"self.kwargs={self.kwargs}")
            # print(f"list_of_dicts={list_of_dicts}")
            # print(f"dict_of_dicts={dict_of_dicts}")
            csl = cube_game.CubeboxesStatusList.make_from_json(json_statuses)
            # print(f"csl={csl}")
            return csl
        except Exception as e:
            CubeLogger.static_error(f"Error parsing CubeboxesStatusList from CubeMsgReplyAllCubeboxesStatuses: {e}")
            return None


class CubeMsgRequestAllCubeboxesStatusHashes(CubeMessage):
    """Sent from a node to the CubeMaster to ask for the hashes of the status of all cubeboxes."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUS_HASHES, sender)
        self.require_ack = False


class CubeMsgReplyAllCubeboxesStatusHashes(CubeMessage):
    """Sent from the CubeMaster to a node in response to a REQUEST_ALL_CUBEBOXES_STATUS_HASHES message."""

    def __init__(self, sender=None, hashes: Dict[NodeName, Hash] = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_ALL_CUBEBOXES_STATUS_HASHES, sender)
            if hashes:
                self.kwargs["hashes"] = json.dumps(hashes)
        self.require_ack = False

    @property
    def hash_dict(self) -> dict:
        # parse self.kwargs.get("hashes") to a dict
        return json.loads(self.kwargs.get("hashes"))


# team status request & reply

class CubeMsgRequestTeamStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of a team."""

    def __init__(self, sender=None, team_name=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REQUEST_TEAM_STATUS, sender, team_name=team_name)
        self.require_ack = True

    @property
    def team_name(self) -> str:
        return str(self.kwargs.get("team_name"))


class CubeMsgReplyTeamStatus(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_TEAM_STATUS message."""

    def __init__(self, sender=None, status: cube_game.CubeTeamStatus = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_TEAM_STATUS, sender)
            if status:
                self.kwargs["cubebox_status"] = status.to_json()
        self.require_ack = False

    @property
    def team_status(self) -> cube_game.CubeTeamStatus:
        json_status = self.kwargs.get("cubebox_status", None)
        # CubeLogger.static_debug(f"CubeMsgReplyTeamStatus : json_status={json_status}")
        return cube_game.CubeTeamStatus.make_from_json(json_status)


class CubeMsgRequestAllTeamsStatusHashes(CubeMessage):
    """Sent from a node to the CubeMaster to ask for the hashes of the status of all teams."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_TEAMS_STATUS_HASHES, sender)
        self.require_ack = False


class CubeMsgReplyAllTeamsStatusHashes(CubeMessage):
    """Sent from the CubeMaster to a node in response to a REQUEST_ALL_TEAMS_STATUS_HASHES message."""

    def __init__(self, sender=None, hashes: Dict[TeamName, Hash] = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_ALL_TEAMS_STATUS_HASHES, sender)
            if hashes:
                self.kwargs["hashes"] = json.dumps(hashes)
        self.require_ack = False

    @property
    def hash_dict(self) -> dict:
        # parse self.kwargs.get("hashes") to a dict
        return json.loads(self.kwargs.get("hashes"))


class CubeMsgRequestAllTeamsStatuses(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of all teams."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_TEAMS_STATUSES, sender)
        self.require_ack = False

class CubeMsgReplyAllTeamsStatuses(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_ALL_TEAMS_STATUSES message."""

    def __init__(self, sender=None, statuses: cube_game.CubeTeamsStatusList = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REPLY_ALL_TEAMS_STATUSES, sender, statuses=statuses)
            if statuses:
                self.kwargs[cube_game.CubeTeamsStatusList.JSON_ROOT_OBJECT_NAME] = statuses.to_json()
        self.require_ack = False

    @property
    def teams_statuses(self) -> Optional[cube_game.CubeTeamsStatusList]:
        # parse self.kwargs.get("statuses") to a dict
        try:
            json_statuses = self.kwargs.get(cube_game.CubeTeamsStatusList.JSON_ROOT_OBJECT_NAME)
            tsl = cube_game.CubeTeamsStatusList.make_from_json(json_statuses)
            return tsl
        except Exception as e:
            CubeLogger.static_error(f"Error parsing TeamsStatusList from CubeMsgReplyAllTeamsStatuses: {e}")
            return None

# orders

class CubeMsgOrderCubeboxToWaitForReset(CubeMessage):
    """Sent from the CubeMaster to a CubeBox to order it to wait for a reset."""

    def __init__(self, sender=None, cube_id=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.ORDER_CUBEBOX_TO_WAIT_FOR_RESET, sender, cube_id=cube_id)
        self.require_ack = True

    @property
    def cube_id(self) -> int:
        return int(self.kwargs.get("cube_id"))

class CubeMsgOrderCubeboxToReset(CubeMessage):
    """Sent from the CubeMaster to a CubeBox to order it to reset."""

    def __init__(self, sender=None, cube_id=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.ORDER_CUBEBOX_TO_RESET, sender, cube_id=cube_id)
        self.require_ack = True

    @property
    def cube_id(self) -> int:
        return int(self.kwargs.get("cube_id"))


# common messages

class CubeMsgAck(CubeMessage):
    """Sent from a node to another node to acknowledge a message.
    The `info` parameter can be used to give more information about the acknowledgement.
    See the CubeMsgReplies enumeration for the standard values."""

    def __init__(self, sender: str = None, acked_msg: CubeMessage = None, info: CubeAckInfos = None,
                 copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(msgtype=CubeMsgTypes.ACK, sender=sender, acked_hash=acked_msg.hash, info=info)
        self.require_ack = False

    @property
    def info(self) -> CubeAckInfos:
        return self.kwargs.get("info", CubeAckInfos.NONE)


class CubeMsgHeartbeat(CubeMessage):
    """Sent from a node to everyone to signal its presence."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.HEARTBEAT, sender)
        self.require_ack = False


class CubeMsgWhoIs(CubeMessage):
    """Sent from whatever node to everyone to ask who is a specific node (asking for IP)."""

    def __init__(self, sender=None, node_name_to_find=None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.WHO_IS, sender, node_name_to_find=node_name_to_find)
        self.require_ack = False

    @property
    def node_name_to_find(self) -> NodeName:
        return str(self.kwargs.get("node_name_to_find"))


# test functions

def test_make_from_message():
    add_team_msg_1 = CubeMsgFrontdeskNewTeam("CubeFrontDesk",
                                             cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890",
                                                                      max_time_sec=1200))
    ack_msg_1 = CubeMsgAck("CubeMaster", add_team_msg_1, info=CubeAckInfos.OK)
    msg_from_ack = CubeMessage(copy_msg=ack_msg_1)
    msg_from_team = CubeMessage(copy_msg=add_team_msg_1)
    ack_msg_2 = CubeMsgAck(copy_msg=msg_from_ack)
    add_team_msg_2 = CubeMsgFrontdeskNewTeam(copy_msg=msg_from_team)

    print(f"add_team_msg_1 ({add_team_msg_1.hash}) :", add_team_msg_1)
    print(f"ack_msg_1 ({ack_msg_1.hash}) :", ack_msg_1)
    print(f"msg_from_ack ({msg_from_ack.hash}) :", msg_from_ack)
    print(f"msg_from_team ({msg_from_team.hash}) :", msg_from_team)
    print(f"ack_msg_2 ({ack_msg_2.hash}) :", ack_msg_2)
    print(f"add_team_msg_2 ({add_team_msg_2.hash}) :", add_team_msg_2)

    print("test_make_from_message PASSED for CubeMsgNewTeam and CubeMsgAck")

    assert ack_msg_1.to_string() == ack_msg_2.to_string()
    assert add_team_msg_1.to_string() == add_team_msg_2.to_string()
    assert ack_msg_1.info == ack_msg_2.info
    assert add_team_msg_1.team.name == add_team_msg_2.team.name
    assert add_team_msg_1.team.rfid_uid == add_team_msg_2.team.rfid_uid
    assert add_team_msg_1.team.max_time_sec == add_team_msg_2.team.max_time_sec

    cbp_msg = CubeMsgButtonPress("CubeBox1", start_timestamp=10, press_timestamp=20)
    msg = CubeMessage(copy_msg=cbp_msg)
    cbp_msg_2 = CubeMsgButtonPress(copy_msg=msg)
    print(f"cbp_msg : {cbp_msg}")
    print(f"msg : {msg}")
    print(f"cbp_msg_2 : {cbp_msg_2}")

    assert cbp_msg.to_string() == cbp_msg_2.to_string()
    assert cbp_msg.start_timestamp == cbp_msg_2.start_timestamp
    assert cbp_msg.press_timestamp == cbp_msg_2.press_timestamp
    assert cbp_msg.start_timestamp == 10
    assert cbp_msg.press_timestamp == 20

    status = cube_game.CubeboxStatus(cube_id=1,
                                     current_team_name="Team1",
                                     start_timestamp=11,
                                     end_timestamp=20,
                                     last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="1234567890", timestamp=10),
                                     state=cube_game.CubeboxState.STATE_READY_TO_PLAY)

    cmcsr = CubeMsgReplyCubeboxStatus(sender="CubeMaster", status=status)
    print(f"cmcsr={cmcsr}")
    print(f"cmcsr.status={cmcsr.cubebox}")
    msg = CubeMessage(copy_msg=cmcsr)
    cmcsr_2 = CubeMsgReplyCubeboxStatus(copy_msg=msg)
    print(f"cmcsr_2={cmcsr_2}")
    print(f"cmcsr_2.status={cmcsr_2.cubebox}")

    assert cmcsr.to_string() == cmcsr_2.to_string()
    assert cmcsr.cubebox == cmcsr_2.cubebox

    print("test_make_from_message PASSED for CubeMsgButtonPress")

    print("test_make_from_message PASSED")


def test_message_to_and_from_string(msg_class: Type[CubeMessage], sender: str, **kwargs):
    """test that the message can be converted to a string and back"""
    log = CubeLogger("test_message_to_and_from_string")
    log.setLevel(log.LEVEL_DEBUG +1)
    # noinspection PyBroadException
    try:
        # assert kwargs is not None
        for k in kwargs:
            value_str = str(kwargs[k])
            if kwargs[k] is None:
                continue
            log.debug(f"- kwargs[{k}] : {type(kwargs[k]).__name__} = '{value_str}'")
        kwargs_str = f", ".join([f"{k}={v}" for k, v in kwargs.items()])
    except Exception as e:
        # log.warning(f"Error parsing kwargs: {e}", exc_info=True)
        log.warning(f"Error parsing kwargs (this might be expected): {e}")
        kwargs = {}
        kwargs_str = ""

    classname = msg_class.__name__
    log.debug(f"constructing {classname}(sender={sender}, {kwargs_str})")
    # noinspection PyTypeChecker
    msg = msg_class(sender, **kwargs)
    msg_str = msg.to_string()
    log.debug(f"msg={msg}")

    try:
        msg2 = CubeMessage.make_from_string(msg_str)
        assert msg2 == msg
        log.success(f"Passed test_to_and_from_string: {classname}(sender={sender}, {kwargs_str}")
    except Exception as e:
        log.error(f"Failed test_to_and_from_string: {classname}(sender={sender}, {kwargs_str}")
        log.debug(f"msg={msg}")
        log.debug(f"msg.to_string()={msg.to_string()}")
        log.debug(f"msg.make_from_string(msg.to_string())={msg.make_from_string(msg.to_string())}")
        log.debug(f"{e}")


# @formatter:off
def test_all_message_classes_to_and_from_string():
    """for each subclass of CubeMessage, test that the message can be converted to a string and back"""
    test_message_to_and_from_string(CubeMsgFrontdeskNewTeam, "CubeFrontDesk", team=cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890", max_time_sec=1200))
    test_message_to_and_from_string(CubeMsgFrontdeskRemoveTeam, "CubeFrontDesk", team_name="Team1")
    test_message_to_and_from_string(CubeMsgButtonPress, "CubeBox1", start_timestamp=10, press_timestamp=20)
    test_message_to_and_from_string(CubeMsgRfidRead, "CubeBox1", uid="1234567890", timestamp=10)
    test_message_to_and_from_string(CubeMsgRequestAllCubeboxesStatuses, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestAllTeamsStatuses, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestCubeMasterStatusHash, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestAllTeamsStatusHashes, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestAllCubeboxesStatusHashes, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgReplyAllCubeboxesStatusHashes, "CubeMaster", hashes={"CubeBox1": "hash1", "CubeBox2": "hash2"})
    test_message_to_and_from_string(CubeMsgReplyAllTeamsStatusHashes, "CubeMaster", hashes={"Team1": "hash1", "Team2": "hash2"})
    test_message_to_and_from_string(CubeMsgRequestTeamStatus, "CubeFrontDesk", team_name="Team1")
    test_message_to_and_from_string(CubeMsgRequestCubemasterStatus, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestCubeboxStatus, "CubeFrontDesk", cube_id=1)
    test_message_to_and_from_string(CubeMsgAck, "CubeMaster", acked_msg=CubeMessage(CubeMsgTypes.TEST, "CubeFrontDesk"), info=CubeAckInfos.OK)
    test_message_to_and_from_string(CubeMsgHeartbeat, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgRequestVersion, "CubeFrontDesk")
    test_message_to_and_from_string(CubeMsgReplyVersion, "CubeMaster")
    test_message_to_and_from_string(CubeMsgWhoIs, "CubeFrontDesk", node_name_to_find="CubeMaster")
    test_message_to_and_from_string(CubeMsgReplyCubeboxStatus, "CubeMaster", status=cube_game.CubeboxStatus(cube_id=1, current_team_name="Team1", start_timestamp=11, end_timestamp=20, last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="1234567890", timestamp=10), state=cube_game.CubeboxState.STATE_READY_TO_PLAY))
    test_message_to_and_from_string(CubeMsgReplyTeamStatus, "CubeMaster", status=cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890", max_time_sec=1200))
    test_message_to_and_from_string(CubeMsgReplyAllCubeboxesStatuses, "CubeMaster", statuses={"CubeBox1": cube_game.CubeboxStatus(cube_id=1, current_team_name="Team1", start_timestamp=11, end_timestamp=20, last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="1234567890", timestamp=10), state=cube_game.CubeboxState.STATE_READY_TO_PLAY)})
    test_message_to_and_from_string(CubeMsgReplyCubeMasterStatusHash, "CubeMaster", hash="hash1")
    test_message_to_and_from_string(CubeMsgReplyAllTeamsStatuses, "CubeMaster", statuses={"Team1": cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890", max_time_sec=1200)})




# @formatter:on
def test_all_reply_messages():
    """test that all request and reply messages match the objects they are supposed to represent"""
    log = CubeLogger("test_all_request_and_reply_messages")
    defined_cubeboxes = [
        cube_game.CubeboxStatus(cube_id=1, current_team_name="Team1", start_timestamp=11, end_timestamp=20,
                                last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="1234567890", timestamp=10),
                                state=cube_game.CubeboxState.STATE_READY_TO_PLAY),
        cube_game.CubeboxStatus(cube_id=2, current_team_name="Team2", start_timestamp=12, end_timestamp=21,
                                last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="2345678901", timestamp=11),
                                state=cube_game.CubeboxState.STATE_READY_TO_PLAY),
        cube_game.CubeboxStatus(cube_id=3, current_team_name=None, start_timestamp=None, end_timestamp=None
                                , last_valid_rfid_line=None, state=cube_game.CubeboxState.STATE_READY_TO_PLAY),
    ]
    defined_teams = [
        cube_game.CubeTeamStatus(
            name="Team1", custom_name="CustomTeam1", rfid_uid="1234567890", max_time_sec=1100,
            start_timestamp=0,
            completed_cubeboxes=[
                cube_game.CompletedCubeboxStatus(cube_id=1, start_timestamp=10, end_timestamp=20),
                cube_game.CompletedCubeboxStatus(cube_id=2, start_timestamp=11, end_timestamp=21)
            ],
            current_cubebox_id=3,
            trophies=[cube_game.CubeTrophy(name="Trophy1", description="Description1", points=100),
                      cube_game.CubeTrophy(name="Trophy2", description="Description2", points=200),
                      ]
        ),
        cube_game.CubeTeamStatus(
            name="Team2", custom_name="CustomTeam2", rfid_uid="2345678901", max_time_sec=1200,
            start_timestamp=0,
            completed_cubeboxes=[
                cube_game.CompletedCubeboxStatus(cube_id=5, start_timestamp=10, end_timestamp=20),
            ],
            current_cubebox_id=3,
            trophies=[cube_game.CubeTrophy(name="Trophy1", description="Description1", points=100),
                      ]
        ),
        cube_game.CubeTeamStatus(
            name="Team3", custom_name="CustomTeam3", rfid_uid="3456789012", max_time_sec=1300,
            start_timestamp=None,
            completed_cubeboxes=[],
            current_cubebox_id=None,
            trophies=[]
        ),
    ]

    cubeboxes = cube_game.CubeboxesStatusList(cubeboxes=defined_cubeboxes)
    cubebox = cubeboxes[0]
    teams = cube_game.CubeTeamsStatusList(teams=defined_teams)
    team = teams[0]

    msg_reply = CubeMsgReplyAllCubeboxesStatuses("CubeMaster", cubeboxes)
    msg_reply_copy = CubeMsgReplyAllCubeboxesStatuses(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyAllCubeboxesStatuses.make_from_string(msg_reply.to_string())
    assert cubeboxes == msg_reply.cubeboxes_statuses, f"{cubeboxes} != {msg_reply.cubeboxes_statuses}"
    assert cubeboxes == msg_reply_copy.cubeboxes_statuses, f"{cubeboxes} != {msg_reply_copy.cubeboxes_statuses}"
    assert cubeboxes == msg_reply_from_string.cubeboxes_statuses, f"{cubeboxes} != {msg_reply_from_string.cubeboxes_statuses}"
    log.success("CubeMsgReplyAllCubeboxesStatuses PASSED")

    msg_reply = CubeMsgReplyAllTeamsStatuses("CubeMaster", teams)
    msg_reply_copy = CubeMsgReplyAllTeamsStatuses(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyAllTeamsStatuses.make_from_string(msg_reply.to_string())
    assert teams == msg_reply.teams_statuses, f"{teams} != {msg_reply.teams_statuses}"
    assert teams == msg_reply_copy.teams_statuses, f"{teams} != {msg_reply_copy.teams_statuses}"
    assert teams == msg_reply_from_string.teams_statuses, f"{teams} != {msg_reply_from_string.teams_statuses}"
    log.success("CubeMsgReplyAllTeamsStatuses PASSED")

    msg_reply = CubeMsgReplyCubeboxStatus("CubeMaster", cubebox)
    msg_reply_copy = CubeMsgReplyCubeboxStatus(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyCubeboxStatus.make_from_string(msg_reply.to_string())
    assert cubebox == msg_reply.cubebox, f"{cubebox} != {msg_reply.cubebox}"
    assert cubebox == msg_reply_copy.cubebox, f"{cubebox} != {msg_reply_copy.cubebox}"
    assert cubebox == msg_reply_from_string.cubebox, f"{cubebox} != {msg_reply_from_string.cubebox}"
    log.success("CubeMsgReplyCubeboxStatus PASSED")

    msg_reply = CubeMsgReplyTeamStatus("CubeMaster", team)
    msg_reply_copy = CubeMsgReplyTeamStatus(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyTeamStatus.make_from_string(msg_reply.to_string())
    assert team == msg_reply.team_status, f"{team} != {msg_reply.team_status}"
    assert team == msg_reply_copy.team_status, f"{team} != {msg_reply_copy.team_status}"
    assert team == msg_reply_from_string.team_status, f"{team} != {msg_reply_from_string.team_status}"
    log.success("CubeMsgReplyTeamStatus PASSED")

    msg_reply = CubeMsgReplyAllCubeboxesStatusHashes("CubeMaster", hashes=cubeboxes.hash_dict)
    msg_reply_copy = CubeMsgReplyAllCubeboxesStatusHashes(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyAllCubeboxesStatusHashes.make_from_string(msg_reply.to_string())
    assert msg_reply.hash_dict == msg_reply_copy.hash_dict, f"{msg_reply.hash_dict} != {msg_reply_copy.hash_dict}"
    assert msg_reply_copy.hash_dict == msg_reply.hash_dict, f"{msg_reply_copy.hash_dict} != {msg_reply.hash_dict}"
    assert msg_reply_from_string.hash_dict == msg_reply.hash_dict, f"{msg_reply_from_string.hash_dict} != {msg_reply.hash_dict}"
    log.success("CubeMsgReplyAllCubeboxesStatusHashes PASSED")

    msg_reply = CubeMsgReplyAllTeamsStatusHashes("CubeMaster", hashes=teams.hash_dict)
    msg_reply_copy = CubeMsgReplyAllTeamsStatusHashes(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyAllTeamsStatusHashes.make_from_string(msg_reply.to_string())
    assert msg_reply.hash_dict == msg_reply_copy.hash_dict, f"{msg_reply.hash_dict} != {msg_reply_copy.hash_dict}"
    assert msg_reply_copy.hash_dict == msg_reply.hash_dict, f"{msg_reply_copy.hash_dict} != {msg_reply.hash_dict}"
    assert msg_reply_from_string.hash_dict == msg_reply.hash_dict, f"{msg_reply_from_string.hash_dict} != {msg_reply.hash_dict}"
    log.success("CubeMsgReplyAllTeamsStatusHashes PASSED")

    msg_reply = CubeMsgReplyCubeMasterStatusHash("CubeMaster", hash="hash1")
    msg_reply_copy = CubeMsgReplyCubeMasterStatusHash(copy_msg=msg_reply)
    msg_reply_from_string = CubeMsgReplyCubeMasterStatusHash.make_from_string(msg_reply.to_string())
    assert msg_reply.hash == msg_reply_copy.hash, f"{msg_reply.hash} != {msg_reply_copy.hash}"
    assert msg_reply_copy.hash == msg_reply.hash, f"{msg_reply_copy.hash} != {msg_reply.hash}"
    assert msg_reply_from_string.hash == msg_reply.hash, f"{msg_reply_from_string.hash} != {msg_reply.hash}"
    log.success("CubeMsgReplyCubeMasterStatusHash PASSED")

    log.success("test_all_reply_messages PASSED")







if __name__ == "__main__":
    # test_all_message_classes_to_and_from_string()
    test_all_reply_messages()
    exit(0)
    print(CubeMsgReplies.OK)
    ack_msg = CubeMsgAck("CubeMaster", CubeMessage(CubeMsgTypes.TEST, "CubeFrontDesk"), info=CubeMsgReplies.OK)
    print(ack_msg.to_string())
    assert ack_msg.info == CubeMsgReplies.OK
    msg = CubeMessage()
    msg.build_from_string(ack_msg.to_string())
    print("msg=", msg)
    ack_msg_2 = CubeMsgAck(copy_msg=msg)
    print("ack_msg_2=", ack_msg_2)
    assert ack_msg_2.info == CubeMsgReplies.OK, f"'{ack_msg_2.info}' != '{CubeMsgReplies.OK}'"
    exit(0)

    # test the CubeMessage class and all its subclasses
    sender_name = "FooSender"
    print(CubeMessage(CubeMsgType.TEST, sender_name, a=1, b=2, c=3))
    print(CubeMsgRfidRead(sender_name, uid="1234567890", timestamp=time.time()))
    print(CubeMsgButtonPress(sender_name))
    print(CubeMsgNewTeam(sender_name, "Team1", 1200))
