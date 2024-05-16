"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""

import thecubeivazio.cube_game as cube_game

import enum


class CubeMsgTypes(enum.Enum):
    """Enumeration of the different types of messages that can be sent."""
    TEST = 0
    VERSION_REPLY = 10
    VERSION_REQUEST = 22
    HEARTBEAT = 30
    # sent from a node to another node to acknowledge that the message has been received and handled.
    # can include an info, see the MsgAck class for standard values for `info`
    ACK = 40
    WHO_IS = 45
    I_AM = 50

    # Cubebox messages
    CUBEBOX_RFID_READ = 100
    CUBEBOX_BUTTON_PRESS = 110

    # Cubeserver messages
    CUBESERVER_SCORESHEET = 200
    CUBESERVER_TIME_IS_UP = 210
    CUBESERVER_PLAYING_TEAMS = 220

    # Frontdesk messages
    FRONTDESK_NEW_TEAM = 300


class CubeMsgReplies(enum.Enum):
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

    def __init__(self, msgtype: CubeMsgTypes=None, sender: str=None, copy_msg: 'CubeMessage'=None, **kwargs):
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
        """Returns an alphanumeric hash of the message 10 chars long."""
        import hashlib
        return hashlib.md5(self.to_string().encode()).hexdigest()[:10]

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


# TODO: use the info field in cubeserver to tell the cubebox: "valid or invalid button press", "valid or invalid RFID read"
class CubeMsgAck(CubeMessage):
    """Sent from a node to another node to acknowledge a message."""


    def __init__(self, sender:str=None, acked_msg:CubeMessage=None, info:CubeMsgReplies=None, copy_msg:CubeMessage=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
            return
        super().__init__(msgtype=CubeMsgTypes.ACK, sender=sender, acked_hash=acked_msg.hash, info=info)
        self.require_ack = False

    @property
    def info(self):
        return self.kwargs.get("info", CubeMsgReplies.NONE)


class CubeMsgNewTeam(CubeMessage):
    """Sent from the Frontdesk to the CubeServer when a new team is registered."""

    def __init__(self, sender=None, team:cube_game.CubeTeamStatus=None, copy_msg:CubeMessage=None):
        if copy_msg is not None:
            super().__init__(copy_msg=copy_msg)
            return
        super().__init__(CubeMsgTypes.FRONTDESK_NEW_TEAM, sender, name=team.name, rfid_uid=team.rfid_uid, max_time_sec=team.max_time_sec)
        self.require_ack = True

    @property
    def team(self):
        return cube_game.CubeTeamStatus(name=self.kwargs["name"], rfid_uid=self.kwargs["rfid_uid"], allocated_time=self.kwargs["max_time_sec"])


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






class CubeMsgRfidRead(CubeMessage):
    """Sent from the CubeBox to the CubeServer when an RFID tag is read."""

    def __init__(self, sender, uid, timestamp):
        super().__init__(CubeMsgTypes.CUBEBOX_RFID_READ, sender, uid=uid, timestamp=timestamp)


class CubeMsgButtonPress(CubeMessage):
    """Sent from the CubeBox to the CubeServer when the button is pressed."""

    def __init__(self, sender):
        super().__init__(CubeMsgTypes.CUBEBOX_BUTTON_PRESS, sender)
        self.require_ack = True


class CubeMsgScoresheet(CubeMessage):
    """Sent from the CubeServer to the Frontdesk to update the scoresheet of a team that just finished playing."""

    def __init__(self, sender, scoresheet):
        super().__init__(CubeMsgTypes.CUBEBOX_BUTTON_PRESS, sender, scoresheet=scoresheet)
        self.require_ack = True


class CubeMsgTimeIsUp(CubeMessage):
    def __init__(self, sender, team):
        super().__init__(CubeMsgTypes.CUBESERVER_TIME_IS_UP, sender, team=team)


def test_make_from_message():
    add_team_msg_1 = CubeMsgNewTeam("CubeFrontDesk", cube_game.CubeTeamStatus(name="Team1", rfid_uid="1234567890", allocated_time=1200))
    ack_msg_1 = CubeMsgAck("CubeServer", add_team_msg_1, info=CubeMsgReplies.OK)
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

    assert ack_msg_1.to_string() == ack_msg_2.to_string()
    assert add_team_msg_1.to_string() == add_team_msg_2.to_string()
    print("test_make_from_message PASSED")

if __name__ == "__main__":
    print(CubeMsgReplies.OK)
    ack_msg = CubeMsgAck("CubeServer", CubeMessage(CubeMsgTypes.TEST, "CubeFrontDesk"), info=CubeMsgReplies.OK)
    print(ack_msg.to_string())
    assert ack_msg.info == CubeMsgReplies.OK
    msg = CubeMessage()
    msg.build_from_string(ack_msg.to_string())
    print("msg=", msg)
    ack_msg_2 = CubeMsgAck(copy_msg=msg)
    print("ack_msg_2=", ack_msg_2)
    assert ack_msg_2.info == CubeMsgReplies.OK, f"'{ack_msg_2.info}' != '{CubeMsgReplies.OK}'"
    exit(0)
    test_make_from_message()
    exit(0)
    # test the CubeMessage class and all its subclasses
    sender_name = "FooSender"
    print(CubeMessage(CubeMsgType.TEST, sender_name, a=1, b=2, c=3))
    print(CubeMsgRfidRead(sender_name, uid="1234567890", timestamp=time.time()))
    print(CubeMsgButtonPress(sender_name))
    print(CubeMsgNewTeam(sender_name, "Team1", 1200))
