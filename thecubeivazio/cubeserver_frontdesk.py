"""The backend of the cube front desk system. Meant to be implemented by cubegui"""

import threading
import time
from typing import Optional, Iterable, Sized

from thecubeivazio import cube_config

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game
from thecubeivazio.cube_common_defines import Seconds


class CubeServerFrontdesk:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.CubeLogger(name=cubeid.CUBEFRONTDESK_NAME,
                                          log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # load the config
        self.config = cube_config.CubeConfig()

        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEFRONTDESK_NAME,
                                          log_filename=cube_logger.CUBEFRONTDESK_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # params for threading
        self._msg_handling_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        # holds the information about the teams
        # TODO: do something with them. update them, request updates, etc
        self.teams = cube_game.CubeTeamsStatusList()
        self.cubeboxes = cube_game.CubeboxStatusList()

    def run(self):
        self.rfid.run()

        self._msg_handling_thread = threading.Thread(target=self._msg_handling_loop)
        self._keep_running = True
        self._msg_handling_thread.start()

        # self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self._keep_running = False
        self.net.stop()
        self.rfid.stop()
        self._msg_handling_thread.join(timeout=0.1)

    def _msg_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            # print(":", end="")
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                elif message.msgtype == cm.CubeMsgTypes.CUBEMASTER_SCORESHEET:
                    self.log.info(f"Received scoresheet message from {message.sender}")
                    self.net.acknowledge_this_message(message)
                elif message.msgtype == cm.CubeMsgTypes.CUBEMASTER_TEAM_WIN:
                    self.log.info(f"Received team win message from {message.sender}")
                    # TODO: do something with it
                    # TODO: wait, the Frontdesk can already receive the team win message from the CubeBox if we're on UDP broadcast
                    #  should i handle it anyway just in case i move to TCP or addressed UDP later on?
                    self.net.acknowledge_this_message(message)
                else:
                    self.log.warning(f"Unhandled message type: {message.msgtype}. Removing")
                    self.net.remove_msg_from_incoming_queue(message)
                # TODO: handle other message types

    def add_new_team(self, team: cube_game.CubeTeamStatus) -> cubenet.SendReport:
        """Send a message to the CubeMaster to add a new team. Return True if the CubeMaster added the team, False if not, None if no response."""
        msg = cm.CubeMsgNewTeam(self.net.node_name, team)
        report = self.net.send_msg_to_cubeserver(msg, require_ack=True)
        if not report:
            self.log.error(f"Failed to send the new team message : {team.name}")
            return report
        ack_msg = report.ack_msg
        self.log.debug(f"add_new_team ack_msg={ack_msg.to_string() if ack_msg else None}")
        if ack_msg is None:
            self.log.error(f"The CubeMaster did not respond to the new team message : {team.name}")
        elif ack_msg.info == cm.CubeAckInfos.OK:
            self.log.info(f"The CubeMaster added the new team : {team.name}")
        else:
            self.log.error(f"The CubeMaster did not add the new team : {team.name} ; info={ack_msg.info}")
        return report


class CubeServerFrontdeskWithPrompt(CubeServerFrontdesk):
    def __init__(self):
        super().__init__()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit : stop the CubeFrontdesk and exit the program")
        print("h, help : display this help")
        print("t, teams : display the list of teams")
        print("cb, cubeboxes : display the list of cubeboxes")
        print("ni, netinfo : display the network nodes info")
        print("wi, whois : send a WhoIs message to all nodes")
        print("at, addteam (name [, custom_name, uid, max_time_sec]) : add a new team")
        print("atr, addtrophy (team_name, name [, points, description, image_path]) : add a new trophy")
        print("rcms, requestcubemasterstatus : request the CubeMaster status")

    def stop(self):
        super().stop()

    def run(self, no_prompt=False):
        super().run()
        # stop the rfid listener since we're gonna press the enter key a lot while using the prompt
        self.rfid.stop()
        if no_prompt:
            return
        try:
            self.prompt_loop()
        except KeyboardInterrupt:
            print("KeyboardInterrupt. Stopping the CubeFrontdesk")
            self.stop()

    @staticmethod
    def pad_args(argslist: Sized, *defaults):
        ret = list(argslist) + list(defaults)
        print(f"pad_args: {ret}")
        return ret

    def prompt_loop(self):
        while True:
            line = input("CubeFrontdesk Command > ")
            self.handle_input(line)

    def handle_input(self, line: str) -> bool:
        cmd = line.split()[0] if line else None
        args = line.split()[1:]
        if not cmd:
            return True
        elif cmd in ["q", "quit"]:
            self.stop()
            return True
        elif cmd in ["h", "help"]:
            self.print_help()
        elif cmd in ["t", "teams"]:
            print(self.teams.to_string())
        elif cmd in ["cb", "cubeboxes"]:
            print(self.cubeboxes.to_string())
        elif cmd in ["ni", "netinfo"]:
            # display the nodes in the network and their info
            print(self.net.nodes_list.to_string())
        elif cmd in ["wi", "whois"]:
            self.net.send_msg_to_all(cm.CubeMsgWhoIs(self.net.node_name, cubeid.EVERYONE_NAME))
        elif cmd in ["at", "addteam"]:
            if len(args) < 3:
                print("Usage: addteam (name [, custom_name, uid, max_time_sec])")
                return False
            # if there are less than 4 args, pad the rest with default values until there are 4 args
            args = self.pad_args(args, "CustomName", "1234567890", 60.0)
            name, custom_name, uid, max_time_sec = args

            max_time_sec = Seconds(max_time_sec)
            team = cube_game.CubeTeamStatus(rfid_uid=uid, name=name, custom_name=custom_name, max_time_sec=max_time_sec)
            self.add_new_team(team)
        elif cmd in ["atr", "addtrophy"]:
            if len(args) < 2:
                print("Usage: ddtrophy (team_name, name [, points, description, image_path])")
                return False
            args = self.pad_args(args, 100, "FooDescription", "foo.png")
            team_name, name, points, description, image_path = args
            team = self.teams.find_team_by_name(team_name)
            if team is None:
                print(f"Team {team_name} not found")
                return False
            points = int(points)
            trophy = cube_game.CubeTeamTrophy(name=name, description=description, points=points, image_path=image_path)
            team.trophies.append(trophy)
            self.log.info(f"Added trophy {trophy.name} to team {team.name}:")
            self.log.info(f"{team}")
        elif cmd in ["rcms", "requestcubemasterstatus"]:
            self.net.send_msg_to_cubeserver(cm.CubeMsgRequestCubemasterStatus())
        else:
            print("Unknown command")
            return False


def test():
    import atexit
    fd = CubeServerFrontdesk()
    atexit.register(fd.stop)

    team_names = ["Budapest",
                  "Debrecen",
                  "Budapest",
                  "Szeged",
                  "Pécs",
                  "Debrecen",
                  "Zalaegerszeg", ]
    for team_name in team_names:
        fd.add_new_team(cube_game.CubeTeamStatus(rfid_uid="1234567890", name=team_name, max_time_sec=60.0))
    time.sleep(5)


def test_prompt_commands():
    import atexit
    fd = CubeServerFrontdeskWithPrompt()
    atexit.register(fd.stop)

    fd.run(no_prompt=True)
    fd.handle_input("at London")


def run_prompt():
    import atexit
    fd = CubeServerFrontdeskWithPrompt()
    atexit.register(fd.stop)
    fd.run()


if __name__ == "__main__":
    run_prompt()
