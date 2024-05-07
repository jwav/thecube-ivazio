"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""

import cube_identification as cubeid

import enum


class CubeMsgType(enum.Enum):
    """Enumeration of the different types of messages that can be sent."""
    TEST = 0
    VERSION_REPLY = 10
    VERSION_REQUEST = 22
    HEARTBEAT = 30
    ACK = 40


    # Cubebox messages
    CUBEBOX_RFID_READ = 100
    CUBEBOX_BUTTON_PRESS = 110

    # Cubeserver messages
    CUBESERVER_SCORESHEET = 200
    CUBESERVER_TIME_IS_UP = 210
    CUBESERVER_PLAYING_TEAMS = 220
    WHO_IS = 230

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
        # must be manually set to False if no acknowledgement is required
        self.require_ack = True
        self.kwargs = kwargs

    def copy(self):
        ret = CubeMessage(self.msgtype, self.sender, **self.kwargs)
        ret.require_ack = self.require_ack
        return ret

    def is_valid(self):
        return all([isinstance(self.sender, str), isinstance(self.msgtype, CubeMsgType), all([isinstance(k, str) for k in self.kwargs.keys()])])

    def to_string(self):
        sep = self.SEPARATOR
        return f"{self.PREFIX}{sep}sender={self.sender}{sep}msgtype={self.msgtype.name}{sep}{sep.join([f'{k}={v}' for k, v in self.kwargs.items()])}"

    def to_bytes(self):
        return self.to_string().encode()

    @staticmethod
    def make_from_bytes(self, msg_bytes:bytes):
        return self.make_from_string(msg_bytes.decode())

    @staticmethod
    def make_from_string(self, msg_str:str):
        sep = self.SEPARATOR
        if not msg_str.startswith(self.PREFIX):
            return None
        parts = msg_str.split(sep)
        if len(parts) < 3:
            return None
        sender = None
        msgtype = None
        kwargs = {}
        for part in parts[1:]:
            key, value = part.split("=")
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
        return self.msgtype == CubeMsgType.ACK and self.kwargs == other.kwargs

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()

class CubeMsgVersionRequest(CubeMessage):
    def __init__(self, sender):
        super().__init__(CubeMsgType.VERSION_REQUEST, sender)
        self.require_ack = False

class CubeMsgVersionReply(CubeMessage):
    def __init__(self, sender):
        from cube_utils import get_git_branch_date
        super().__init__(CubeMsgType.VERSION_REPLY, sender, version=get_git_branch_date())

class CubeMsgNewTeam(CubeMessage):
    def __init__(self, sender, team, max_time_sec):
        super().__init__(CubeMsgType.FRONTDESK_NEW_TEAM, sender, team=team, max_time_sec=max_time_sec)


class CubeMsgRfidRead(CubeMessage):
    def __init__(self, sender, uid):
        super().__init__(CubeMsgType.CUBEBOX_RFID_READ, sender, uid=uid)


class CubeMsgButtonPress(CubeMessage):
    def __init__(self, sender):
        super().__init__(CubeMsgType.CUBEBOX_BUTTON_PRESS, sender)


class CubeMsgScoresheet(CubeMessage):
    def __init__(self, sender, scoresheet):
        super().__init__(CubeMsgType.CUBEBOX_BUTTON_PRESS, sender, scoresheet=scoresheet)


class CubeMsgTimeIsUp(CubeMessage):
    def __init__(self, sender, team):
        super().__init__(CubeMsgType.CUBESERVER_TIME_IS_UP, sender, team=team)


if __name__ == "__main__":
    # test the CubeMessage class and all its subclasses
    sender_name = "FooSender"
    print(CubeMessage(CubeMsgType.TEST, sender_name, a=1, b=2, c=3))
    print(CubeMsgRfidRead(sender_name, "1234567890"))
    print(CubeMsgButtonPress(sender_name))
    print(CubeMsgNewTeam(sender_name, "Team1", 1200))
