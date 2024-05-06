"""Defines the messages that are sent by the cubeboxes, the cubeserver, and the frontdesk."""

import cube_identification as cubeid

import enum

class CubeMsgType(enum.Enum):
    """Enumeration of the different types of messages that can be sent."""
    TEST = 0
    # Cubebox messages
    CUBEBOX_RFID_READ = 100
    CUBEBOX_BUTTON_PRESS = 101

    # Cubeserver messages
    CUBESERVER_SCORESHEET = 200
    CUBESERVER_TIME_IS_UP = 201
    CUBESERVER_PLAYING_TEAMS = 202

    # Frontdesk messages
    FRONTDESK_NEW_TEAM = 300


class CubeMessage:
    """Base class for all messages."""

    def __init__(self, msgtype:CubeMsgType, sender:str, **kwargs):
        self.msgtype = msgtype
        self.sender = sender
        self.kwargs = kwargs

    def to_string(self):
        sep = "|"
        return f"CUBEMSG{sep}sender={self.sender}{sep}msgtype={self.msgtype.name}{sep}{sep.join([f'{k}={v}' for k,v in self.kwargs.items()])}"

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()

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


