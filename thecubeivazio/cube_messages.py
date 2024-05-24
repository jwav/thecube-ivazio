"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""
from typing import Optional

import thecubeivazio.cube_game as cube_game
import thecubeivazio.cube_rfid as cube_rfid

import enum


class CubeMsgTypes(enum.Enum):
    """Enumeration of the different types of messages that can be sent."""
    TEST = 0

    # sent from a node to another node to acknowledge that the message has been received and handled.
    # can include an info, see the MsgAck class for standard values for `info`
    HEARTBEAT = 10
    ACK = 40
    WHO_IS = 45
    I_AM = 50

    VERSION_REPLY = 100
    VERSION_REQUEST = 110
    REQUEST_CUBEBOX_STATUS = 210
    REQUEST_ALL_CUBEBOXES_STATUS = 215
    REQUEST_CUBEMASTER_STATUS = 220
    # REQUEST_FRONTDESK_STATUS = 230
    REQUEST_TEAM_STATUS = 240
    REQUEST_ALL_TEAMS_STATUS = 250
    REQUEST_CUBEMASTER_STATUS_HASH = 260
    REQUEST_TEAMS_STATUS_HASHES = 270
    REQUEST_CUBEBOXES_STATUS_HASHES = 280

    ORDER_CUBEBOX_TO_WAIT_FOR_RESET = 500

    # Messages sent by the CubeBox
    CUBEBOX_RFID_READ = 1000
    CUBEBOX_BUTTON_PRESS = 1100
    # TODO
    CUBEBOX_STATUS_REPLY = 1200
    # TODO
    CUBEBOX_NOTIFY_RESIGNATION = 1300

    # Messages sent by the CubeMaster

    CUBEMASTER_TIME_IS_UP = 2100
    CUBEMASTER_PLAYING_TEAMS = 2200
    CUBEMASTER_TEAM_WIN = 2300
    CUBEMASTER_TEAM_STATUS_REPLY = 2400
    CUBEMASTER_ALL_TEAMS_STATUS_REPLY = 2450
    # TODO: needed?
    CUBEMASTER_CUBEBOX_STATUS = 2500
    CUBEMASTER_ALL_CUBEBOXES_STATUS = 2505
    CUBEMASTER_STATUS_REPLY = 2600

    # Messages sent by the Frontdesk
    FRONTDESK_NEW_TEAM = 3000

    # FRONTDESK_STATUS_REPLY = 3300

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
    @classmethod
    def make_from_message(cls, msg: 'CubeMessage'):
        print("make_from_message : cls=", cls)
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

    def build_from_string(self, msg_str: str):
        sep = CubeMessage.SEPARATOR
        if not msg_str.startswith(CubeMessage.PREFIX):
            return None
        parts = msg_str.split(sep)
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


class CubeMsgNewTeam(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster when a new team is registered."""

    def __init__(self, sender=None, team: cube_game.CubeTeamStatus = None, copy_msg: CubeMessage = None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.FRONTDESK_NEW_TEAM, sender, name=team.name, rfid_uid=team.rfid_uid,
                             max_time_sec=team.max_time_sec)
        self.require_ack = True

    @property
    def team(self) -> cube_game.CubeTeamStatus:
        return cube_game.CubeTeamStatus(name=self.kwargs.get("name"), rfid_uid=self.kwargs.get("rfid_uid"),
                                        max_time_sec=self.kwargs.get("max_time_sec"))


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


class CubeMsgCubeboxWin(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk when a cubebox is won."""

    def __init__(self, sender=None, team_name=None, cube_id=None, start_timestamp=None, win_timestamp=None,
                 copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.CUBEMASTER_TEAM_WIN, sender, team_name=team_name, cube_id=cube_id,
                             start_timestamp=start_timestamp, win_timestamp=win_timestamp)
        self.require_ack = True

    @property
    def team_name(self) -> str:
        return str(self.kwargs.get("team_name"))

    @property
    def cube_id(self) -> int:
        return int(self.kwargs.get("cube_id"))

    @property
    def start_timestamp(self) -> float:
        return float(self.kwargs.get("start_timestamp"))

    @property
    def win_timestamp(self) -> float:
        return float(self.kwargs.get("win_timestamp"))

    @property
    def elapsed_time(self) -> float:
        return self.win_timestamp - self.start_timestamp


class CubeMsgRfidRead(CubeMessage):
    """Sent from the CubeBox to the CubeMaster when an RFID tag is read."""

    def __init__(self, sender=None, uid=None, timestamp=None, copy_msg=None):
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


class CubeMsgCubeboxStatusReply(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_CUBEBOX_STATUS message."""

    def __init__(self, sender=None, status: cube_game.CubeboxStatus = None, copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            kwargs = status.to_kwargs()
            super().__init__(CubeMsgTypes.CUBEBOX_STATUS_REPLY, sender, **kwargs)
        self.require_ack = False

    @property
    def status(self) -> cube_game.CubeboxStatus:
        return cube_game.CubeboxStatus.make_from_kwargs(**self.kwargs)


class CubeMsgRequestAllCubeboxesStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of all cubeboxes."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUS, sender)
        self.require_ack = False


class CubeMsgRequestAllTeamsStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of all teams."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_ALL_TEAMS_STATUS, sender)
        self.require_ack = False


# TODO: implement
class CubeMsgReplyAllTeamsStatus(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_ALL_TEAMS_STATUS message."""

    def __init__(self, sender=None, teams: cube_game.CubeTeamsStatusList = None, copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.CUBEMASTER_ALL_TEAMS_STATUS_REPLY, sender, teams=teams)
        self.require_ack = False

    @property
    def teams(self) -> cube_game.CubeTeamsStatusList:
        return cube_game.CubeTeamsStatusList.make_from_kwargs(self.kwargs)


# TODO:implement
class CubeMsgReplyAllCubeboxesStatus(CubeMessage):
    """Sent from the CubeMaster to the Frontdesk in response to a REQUEST_ALL_CUBEBOXES_STATUS message."""

    def __init__(self, sender=None, cubeboxes: cube_game.CubeboxStatusList = None, copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.CUBEMASTER_ALL_CUBEBOXES_STATUS, sender, cubeboxes=cubeboxes)
        self.require_ack = False

    @property
    def cubeboxes(self) -> cube_game.CubeboxStatusList:
        return cube_game.CubeboxStatusList.make_from_kwargs(self.kwargs)


class CubeMsgRequestTeamStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of a team."""

    def __init__(self, sender=None, team_name=None, copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REQUEST_TEAM_STATUS, sender, team_name=team_name)
        self.require_ack = True

    @property
    def team_name(self) -> str:
        return str(self.kwargs.get("team_name"))


class CubeMsgRequestCubemasterStatus(CubeMessage):
    """Sent from a node to the CubeMaster to ask for its status."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.REQUEST_CUBEMASTER_STATUS, sender)
        self.require_ack = False


class CubeMsgRequestCubeboxStatus(CubeMessage):
    """Sent from the Frontdesk to the CubeMaster to ask for the status of a cubebox."""

    def __init__(self, sender=None, cube_id=None, copy_msg=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
        else:
            super().__init__(CubeMsgTypes.REQUEST_CUBEBOX_STATUS, sender, cube_id=cube_id)
        self.require_ack = True

    @property
    def cube_id(self) -> int:
        return int(self.kwargs.get("cube_id"))


class CubeMsgHeartbeat(CubeMessage):
    """Sent from a node to everyone to signal its presence."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.HEARTBEAT, sender)
        self.require_ack = False


class CubeMsgVersionRequest(CubeMessage):
    """Sent from a node to another node to ask for its version."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.VERSION_REQUEST, sender)
        self.require_ack = False


class CubeMsgVersionReply(CubeMessage):
    """Sent from a node to another node in response to a VERSION_REQUEST message."""

    def __init__(self, sender):
        from cube_utils import get_git_branch_date
        super().__init__(CubeMsgTypes.VERSION_REPLY, sender, version=get_git_branch_date())


class CubeMsgWhoIs(CubeMessage):
    """Sent from whatever node to everyone to ask who is a specific node (asking for IP)."""

    def __init__(self, sender, node_name_to_find):
        super().__init__(CubeMsgTypes.WHO_IS, sender, node_name_to_find=node_name_to_find)
        self.require_ack = False


# TODO: implement in CubeServerMaster
class CubeMsgTimeIsUp(CubeMessage):
    def __init__(self, sender, team):
        super().__init__(CubeMsgTypes.CUBEMASTER_TIME_IS_UP, sender, team=team)


def test_make_from_message():
    add_team_msg_1 = CubeMsgNewTeam("CubeFrontDesk",
                                    cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890", max_time_sec=1200))
    ack_msg_1 = CubeMsgAck("CubeMaster", add_team_msg_1, info=CubeAckInfos.OK)
    msg_from_ack = CubeMessage(copy_msg=ack_msg_1)
    msg_from_team = CubeMessage(copy_msg=add_team_msg_1)
    ack_msg_2 = CubeMsgAck(copy_msg=msg_from_ack)
    add_team_msg_2 = CubeMsgNewTeam(copy_msg=msg_from_team)

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
                                     starting_timestamp=11,
                                     win_timestamp=20,
                                     last_valid_rfid_line=cube_rfid.CubeRfidLine(uid="1234567890", timestamp=10),
                                     state=cube_game.CubeboxState.STATE_READY_TO_PLAY)

    cmcsr = CubeMsgCubeboxStatusReply(sender="CubeMaster", status=status)
    print(f"cmcsr={cmcsr}")
    print(f"cmcsr.status={cmcsr.status}")
    msg = CubeMessage(copy_msg=cmcsr)
    cmcsr_2 = CubeMsgCubeboxStatusReply(copy_msg=msg)
    print(f"cmcsr_2={cmcsr_2}")
    print(f"cmcsr_2.status={cmcsr_2.status}")

    assert cmcsr.to_string() == cmcsr_2.to_string()
    assert cmcsr.status == cmcsr_2.status

    print("test_make_from_message PASSED for CubeMsgButtonPress")

    print("test_make_from_message PASSED")


if __name__ == "__main__":
    test_make_from_message()
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
