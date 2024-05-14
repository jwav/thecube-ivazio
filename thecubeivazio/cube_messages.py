"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""

import thecubeivazio.cube_game as cube_game

import enum
import time


class CubeMsgType(enum.Enum):
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


# TODO: make acknowledgement messages



class CubeMessage:
    """Base class for all messages."""
    SEPARATOR = "|"
    PREFIX = "CUBEMSG"

    def __init__(self, msgtype: CubeMsgType, sender: str, **kwargs):
        self.msgtype = msgtype
        self.sender = sender
        self.sender_ip = None
        # must be manually set to False if no acknowledgement is required
        self.require_ack = True
        self.kwargs = kwargs

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
        return all([isinstance(self.sender, str), isinstance(self.msgtype, CubeMsgType),
                    all([isinstance(k, str) for k in self.kwargs.keys()])])

    def to_string(self):
        sep = self.SEPARATOR
        return f"{self.PREFIX}{sep}sender={self.sender}{sep}msgtype={self.msgtype.name}{sep}{sep.join([f'{k}={v}' for k, v in self.kwargs.items()])}"

    def to_bytes(self):
        return self.to_string().encode()

    @staticmethod
    def make_from_message(msg: 'CubeMessage'):
        return CubeMessage(msg.msgtype, msg.sender, **msg.kwargs)

    @staticmethod
    def make_from_bytes(msg_bytes: bytes):
        return CubeMessage.make_from_string(msg_bytes.decode())

    @staticmethod
    def make_from_string(msg_str: str):
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
        return CubeMessage(CubeMsgType[msgtype], sender, **kwargs)

    def is_ack_of(self, other: 'CubeMessage'):
        """Returns True if this message is an acknowledgement of the other message."""
        return self.msgtype == CubeMsgType.ACK and self.kwargs.get("acked_hash") == other.hash

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()


# TODO: use the info field in cubeserver to tell the cubebox: "valid or invalid button press", "valid or invalid RFID read"
class CubeMsgAck(CubeMessage):
    """Sent from a node to another node to acknowledge a message."""

    INFO_NONE = "NONE"
    INFO_OK = "OK"
    INFO_ERROR = "ERROR"
    INFO_DENIED = "DENIED"
    INFO_INVALID = "INVALID"

    def __init__(self, sender, acked_msg, info=None):
        super().__init__(CubeMsgType.ACK, sender, acked_hash=acked_msg.hash)
        if info is None:
            self.kwargs["info"] = self.INFO_NONE
        self.require_ack = False

class CubeMsgHeartbeat(CubeMessage):
    """Sent from a node to everyone to signal its presence."""

    def __init__(self, sender):
        super().__init__(CubeMsgType.HEARTBEAT, sender)
        self.require_ack = False


class CubeMsgVersionRequest(CubeMessage):
    """Sent from a node to another node to ask for its version."""

    def __init__(self, sender):
        super().__init__(CubeMsgType.VERSION_REQUEST, sender)
        self.require_ack = False


class CubeMsgVersionReply(CubeMessage):
    """Sent from a node to another node in response to a VERSION_REQUEST message."""

    def __init__(self, sender):
        from cube_utils import get_git_branch_date
        super().__init__(CubeMsgType.VERSION_REPLY, sender, version=get_git_branch_date())


class CubeMsgWhoIs(CubeMessage):
    """Sent from whatever node to everyone to ask who is a specific node (asking for IP)."""

    def __init__(self, sender, node_name_to_find):
        super().__init__(CubeMsgType.WHO_IS, sender, node_name_to_find=node_name_to_find)


class CubeMsgIAm(CubeMessage):
    """Sent from whatever node to everyone to announce its presence."""

    def __init__(self, sender):
        super().__init__(CubeMsgType.I_AM, sender)


class CubeMsgNewTeam(CubeMessage):
    """Sent from the Frontdesk to the CubeServer when a new team is registered."""

    def __init__(self, sender, team:cube_game.CubeTeam):
        super().__init__(CubeMsgType.FRONTDESK_NEW_TEAM, sender, name=team.name, rfid_uid=team.rfid_uid, max_time_sec=team.max_time_sec)
        self.require_ack = True


class CubeMsgRfidRead(CubeMessage):
    """Sent from the CubeBox to the CubeServer when an RFID tag is read."""

    def __init__(self, sender, uid, timestamp):
        super().__init__(CubeMsgType.CUBEBOX_RFID_READ, sender, uid=uid, timestamp=timestamp)


class CubeMsgButtonPress(CubeMessage):
    """Sent from the CubeBox to the CubeServer when the button is pressed."""

    def __init__(self, sender):
        super().__init__(CubeMsgType.CUBEBOX_BUTTON_PRESS, sender)
        self.require_ack = True


class CubeMsgScoresheet(CubeMessage):
    """Sent from the CubeServer to the Frontdesk to update the scoresheet of a team that just finished playing."""

    def __init__(self, sender, scoresheet):
        super().__init__(CubeMsgType.CUBEBOX_BUTTON_PRESS, sender, scoresheet=scoresheet)
        self.require_ack = True


class CubeMsgTimeIsUp(CubeMessage):
    def __init__(self, sender, team):
        super().__init__(CubeMsgType.CUBESERVER_TIME_IS_UP, sender, team=team)


if __name__ == "__main__":
    # test the CubeMessage class and all its subclasses
    sender_name = "FooSender"
    print(CubeMessage(CubeMsgType.TEST, sender_name, a=1, b=2, c=3))
    print(CubeMsgRfidRead(sender_name, uid="1234567890", timestamp=time.time()))
    print(CubeMsgButtonPress(sender_name))
    print(CubeMsgNewTeam(sender_name, "Team1", 1200))
