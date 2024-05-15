"""
This module handles everything related to TheCube's central room server, i.e. the raspberrypi4
handling the CubeBoxes, the LED matrix displays, and the web page displayed on an HDMI monitor
"""
import threading
import time

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_game as cube_game

class CubeServer:
    def __init__(self):
        # set up the logger
        self.log = cube_logger.make_logger(name=cubeid.CUBESERVER_NAME, log_filename=cube_logger.CUBESERVER_LOG_FILENAME)
        # set up the networking
        self.net = cubenet.CubeNetworking(node_name=cubeid.CUBESERVER_NAME, log_filename=cube_logger.CUBESERVER_LOG_FILENAME)
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

    def run(self):
        self._rfid_thread = threading.Thread(target=self._rfid_loop)
        self._networking_thread = threading.Thread(target=self._networking_loop)
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
        # TODO

    def _networking_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            #print(":", end="")
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            messages = self.net.get_incoming_msg_queue()
            for message in messages:
                self.log.debug(f"Received message: ({message.hash}) : {message}")
                if message.msgtype == cm.CubeMsgType.CUBEBOX_RFID_READ:
                    self.log.info(f"Received RFID read message from {message.sender}")
                    self.net.acknowledge_message(message)
                elif message.msgtype == cm.CubeMsgType.CUBEBOX_BUTTON_PRESS:
                    self.log.info(f"Received button press message from {message.sender}")
                    self.net.acknowledge_message(message)
                elif message.msgtype == cm.CubeMsgType.FRONTDESK_NEW_TEAM:
                    # TODO
                    self.net.acknowledge_message(message)
                else:
                    self.net.remove_msg_from_incoming_queue(message)
                # TODO: handle other message types

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
                    self.log.info("MUST HANDLE CUBESERVER RFID READ MESSAGE")
                    self.rfid.remove_line(line)

    def _display_loop(self):
        # TODO: implement LCD matrix display
        while self._keep_running:
            pass

    def _webpage_loop(self):
        # TODO: implement webpage
        while self._keep_running:
            pass

class CubeServerWithPrompt:
    def __init__(self):
        self.cs = CubeServer()

    @staticmethod
    def print_help():
        print("Commands:")
        print("q, quit: stops the CubeServer")
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
            cmd = input("CubeServer Command > ")
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
                print(self.cs.ogs.teams_list.to_string())
            elif cmd in ["cg", "cubegames"]:
                print(self.cs.ogs.cubegames_list.to_string())
            elif cmd in ["ni", "netinfo"]:
                # display the nodes in the network and their info
                print(self.cs.net.nodes_list.to_string())
            elif cmd in ["wi", "whois"]:
                self.cs.net.send_msg_to_all(cm.CubeMsgWhoIs(self.cs.net.node_name, cubeid.EVERYONE_NAME))
            else:
                print("Unknown command")

if __name__ == "__main__":
    import atexit

    cs = CubeServerWithPrompt()
    atexit.register(cs.stop)
    try:
        cs.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Stopping CubeServer...")
    finally:
        cs.stop()
