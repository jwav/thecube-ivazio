"""
This module handles everything related to TheCube's central room server, i.e. the raspberrypi4
handling the CubeBoxes, the LED matrix displays, and the web page displayed on an HDMI monitor
"""
import threading
import time

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game
from thecubeivazio import cube_messages as cm

class CubeMasterMaster:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.make_logger(name=cubeid.CUBEMASTER_NAME, log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBEMASTER_NAME, log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        # instanciate the RFID listener
        self.rfid = cube_rfid.CubeRfidKeyboardListener()

        # params for threading
        self._rfid_thread = None
        self._networking_thread = None
        self._webpage_thread = None
        self._display_thread = None
        self._keep_running = False

        # heartbeat setup
        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self.teams = cube_game.CubeTeamsStatusList()
        self.cubeboxes = cube_game.CubeboxStatusList()

    def run(self):
        self._rfid_thread = threading.Thread(target=self._rfid_loop)
        self._networking_thread = threading.Thread(target=self._message_handling_loop)
        self._webpage_thread = threading.Thread(target=self._webpage_loop)
        self._display_thread = threading.Thread(target=self._display_loop)
        self._keep_running = True
        self._rfid_thread.start()
        self._networking_thread.start()
        self._webpage_thread.start()
        self._display_thread.start()

        self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))

    def stop(self):
        self.net.stop()
        self.rfid.stop()
        self._keep_running = False
        self._networking_thread.join(timeout=0.1)
        self._rfid_thread.join(timeout=0.1)
        self._webpage_thread.join(timeout=0.1)
        self._display_thread.join(timeout=0.1)

    def _message_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                # ignore ACK messages. They are to be handled in wait_for_ack_of()
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                # handle RFID read messages from the cubeboxes
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_RFID_READ:
                    self.log.info(f"Received RFID read message from {message.sender}")
                    self.net.acknowledge_this_message(message)
                # handle button press messages from the cubeboxes
                elif message.msgtype == cm.CubeMsgTypes.CUBEBOX_BUTTON_PRESS:
                    self.log.info(f"Received button press message from {message.sender}")
                    # update teams and cubegames to reflect the fact that this cubebox was just won by the team currently playing it
                    # first, check if it's a valid button press (i.e. a valid team is currently playing it)
                    cubebox:cube_game.CubeboxStatus = self.cubeboxes.find_cubebox_by_node_name(message.sender)
                    team = self.teams.find_team_by_cube_id(cubebox.cube_id)
                    if not cubebox:
                        self.log.error(f"WHAT?! Cubebox not found: {message.sender} (this should NOT happen. There's bad code somewhere)")
                        self.net.acknowledge_this_message(message, cm.CubeMsgReplies.ERROR)
                        continue
                    if not team:
                        self.log.error(f"No team is playing that cubebox: {cubebox.cube_id}")
                        self.net.acknowledge_this_message(message, cm.CubeMsgReplies.INVALID)
                        continue
                    # ok, it's a valid button press, which means a team is playing this cubebox. Let's record that win
                    cbp_msg = cm.CubeMsgButtonPress(copy_msg=message)
                    # update the local cubeboxes teams status lists
                    cubebox.reset()
                    self.cubeboxes.update_cubebox(cubebox)
                    team.set_completed_cube(cubebox.cube_id, cbp_msg.start_timestamp, cbp_msg.win_timestamp)
                    self.teams.update_team(team)
                    self.log.info(f"Team {team.name} won cubebox {cubebox.cube_id} in {cbp_msg.win_timestamp - cbp_msg.start_timestamp} seconds")
                    self.net.acknowledge_this_message(message, cm.CubeMsgReplies.OK)

                    # now notify the front desk of the win
                    win_msg = cm.CubeMsgCubeboxWin(self.net.node_name, team.name, cubebox.cube_id, cbp_msg.start_timestamp, cbp_msg.win_timestamp)
                    report = self.net.send_msg_to_frontdesk(win_msg, require_ack=True)
                    if not report:
                        self.log.error(f"Failed to send cubebox win message to frontdesk")
                        continue
                    ack_msg = report.ack_msg
                    if not ack_msg:
                        self.log.error(f"Sent cubebox win message to frontdesk but no ack received")
                        continue
                    else:
                        self.log.info(f"Cubebox win message sent to and acked by frontdesk")
                # handle new team messages from the frontdesk
                elif message.msgtype == cm.CubeMsgTypes.FRONTDESK_NEW_TEAM:
                    self.log.info(f"Received new team message from {message.sender}")
                    ntmsg = cm.CubeMsgNewTeam(copy_msg=message)
                    self.log.info(f"New team: {ntmsg.team.to_string()}")
                    if self.teams.find_team_by_name(ntmsg.team.name):
                        self.log.error(f"Team already exists: {ntmsg.team.name}")
                        self.net.acknowledge_this_message(message, cm.CubeMsgReplies.OCCUPIED)
                    elif self.teams.add_team(ntmsg.team):
                        self.log.info(f"Added new team: {ntmsg.team.name}")
                        self.net.acknowledge_this_message(message, cm.CubeMsgReplies.OK)
                    else:
                        self.log.error(f"Failed to add new team: {ntmsg.team.name}")
                        self.net.acknowledge_this_message(message, cm.CubeMsgReplies.ERROR)
                else:
                    self.log.warning(f"Unhandled message : ({message.hash}) : {message}. Removing")
                    self.net.remove_msg_from_incoming_queue(message)

    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        # TODO: re-enable RFID listener on the server once the tests are over
        # TESTING : disable the RFID listener on the server for now
        return
        self.rfid.run()
        while self._keep_running:
            for line in self.rfid.get_completed_lines():
                print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                if line.is_valid():
                    # TODO: handle the RFID read message
                    self.log.info("MUST HANDLE CUBEMASTER RFID READ MESSAGE")
                    self.rfid.remove_line(line)

    def _display_loop(self):
        # TODO: implement LCD matrix display
        while self._keep_running:
            pass

    def _webpage_loop(self):
        # TODO: implement webpage
        while self._keep_running:
            pass

class CubeMasterWithPrompt:
    def __init__(self):
        self.cs = CubeMasterMaster()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit: stops the CubeMaster")
        print("h, help: prints this help message")
        print("ni, netinfo: prints the network information")
        print("wi, whois: sends WHO_IS message to everyone")
        print("t, teams: prints the list of teams")
        print("cg: show cubegames")
        print("ogs: overall game status")


    def stop(self):
        self.cs.stop()

    def run(self):
        self.cs.run()
        while True:
            cmd = input("CubeMaster Command > ")
            if not cmd:
                continue
            elif cmd in ["q", "quit"]:
                self.stop()
                break
            elif cmd in ["h", "help"]:
                self.print_help()
            elif cmd in ["g", "games"]:
                print("Not implemented yet")
            elif cmd in ["t", "teams"]:
                print(self.cs.teams.to_string())
            elif cmd in ["cg", "cubegames"]:
                print(self.cs.cubeboxes.to_string())
            elif cmd in ["ni", "netinfo"]:
                # display the nodes in the network and their info
                print(self.cs.net.nodes_list.to_string())
            elif cmd in ["wi", "whois"]:
                self.cs.net.send_msg_to_all(cm.CubeMsgWhoIs(self.cs.net.node_name, cubeid.EVERYONE_NAME))
            else:
                print("Unknown command")

if __name__ == "__main__":
    import atexit

    cs = CubeMasterWithPrompt()
    atexit.register(cs.stop)
    try:
        cs.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeMaster...")
    finally:
        cs.stop()
