"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""
import threading
import time

import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_button as cube_button
import thecubeivazio.cube_buzzer as cube_buzzer
from thecubeivazio.cube_common_defines import *

print("cube logger contents:")
print(dir(cube_logger))


# TODO: what happens if a team badges in, and just gives up? The box will be locked forever.
#  we could say: if another team badges in, the first team is automatically badged out.

class CubeServerCubebox:
    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.net = cubenet.CubeNetworking(node_name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.net.ACK_NB_TRIES = 999
        self.rfid = cube_rfid.CubeRfidKeyboardListener()
        # self.rfid = cube_rfid.CubeRfidEventListener()
        self.button = cube_button.CubeButton()
        self.buzzer = cube_buzzer.CubeBuzzer()

        # the last valid RFID and acknowledged line read
        self.last_rfid_line: cube_rfid.CubeRfidLine = None

        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self._thread_rfid = None
        self._thread_button = None
        self._thread_networking = None

        self._keep_running = False

    @property
    def is_box_being_played(self):
        return self.last_rfid_line is not None

    def set_as_not_playing(self):
        self.last_rfid_line = None

    def to_string(self):
        ret = f"CubeServerCubebox({self.net.node_name})\n"
        ret += f"- last_rfid_line: {self.last_rfid_line}\n"
        ret += f"- is_box_being_played: {self.is_box_being_played}\n"
        ret += f"- play_start_timestamp: {self.play_start_timestamp}\n"
        return ret

    @property
    def play_start_timestamp(self):
        if self.last_rfid_line is not None:
            return self.last_rfid_line.timestamp

    def get_cubebox_index(self):
        """Extract the cubebox index from the node name"""
        return cubeid.node_name_to_cubebox_index(self.net.node_name)

    def run(self):
        """Start the RFID, button, and networking threads"""
        self._thread_rfid = threading.Thread(target=self._rfid_loop)
        self._thread_button = threading.Thread(target=self._button_loop)
        self._thread_networking = threading.Thread(target=self._networking_loop)
        self._keep_running = True
        self._thread_rfid.start()
        self._thread_button.start()
        self._thread_networking.start()

    def stop(self):
        """Stop the RFID, button, and networking threads"""
        self._keep_running = False
        self._thread_rfid.join(timeout=0.1)
        self._thread_button.join(timeout=0.1)
        self._thread_networking.join(timeout=0.1)

    def _networking_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            for message in self.net.get_incoming_msg_queue():
                # TODO: does the cubebox need to handle any incoming messages?
                pass
        self.net.stop()

    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        self.rfid.run()
        while self._keep_running:
            time.sleep(0.1)
            for rfid_line in self.rfid.get_completed_lines():
                self.log.info(
                    f"Line entered at {rfid_line.timestamp}: {rfid_line.uid} : {'valid' if rfid_line.is_valid() else 'invalid'}")
                if rfid_line.is_valid():
                    # if the box is already being played, check if the same team is trying to play it again.
                    # if so, ignore the read. If not, badge out the previous team and badge in the new team.
                    if self.is_box_being_played:
                        if rfid_line.uid == self.last_rfid_line.uid:
                            self.log.info("This box is already being played by this team. Ignoring RFID read.")
                        else:
                            self.log.info(
                                "This box is already being played by another team. We're badging out the previous team.")
                            self.badge_out_current_team(play_game_over_sound=True)
                            self.badge_in_new_team(rfid_line)
                    # if the box is not being played, simply badge in the new team
                    else:
                        self.badge_in_new_team(rfid_line)
                self.rfid.remove_line(rfid_line)

    def badge_in_new_team(self, rfid_line: cube_rfid.CubeRfidLine):
        self.log.info(f"Badging in team with RFID {rfid_line.uid}...")
        if self.last_rfid_line is not None:
            self.log.warning("Trying to badge in the same team that's already playing. Ignoring.")
            return
        report = self.net.send_msg_to_cubeserver(
            cm.CubeMsgRfidRead(self.net.node_name, uid=rfid_line.uid, timestamp=rfid_line.timestamp), require_ack=True)
        if not report.success:
            self.log.error("Failed to send RFID read message to CubeMaster")
            self.buzzer.play_rfid_error_sound()
        if not report.ack_msg:
            self.log.error("Sent RFID messages but the CubeMaster did not acknowledge it")
            self.buzzer.play_rfid_error_sound()
        else:
            self.log.info("RFID read message sent to and okayed by the CubeMaster")
            self.last_rfid_line = rfid_line
            self.log.info(f"is_box_being_played={self.is_box_being_played}, last_rfid_line={self.last_rfid_line}")
            self.buzzer.play_rfid_ok_sound()

    def badge_out_current_team(self, play_game_over_sound=False):
        # TODO: send a message to the CubeMaster to badge out the team?
        #  i dont think it's needed. The CubeMaster handles this on itw own.
        if self.last_rfid_line is None:
            self.log.warning("Trying to badge out a team but there is no team to badge out")
        else:
            self.log.info(f"Badging out team with RFID {self.last_rfid_line.uid}")
            if play_game_over_sound:
                self.buzzer.play_game_over_sound()
        self.set_as_not_playing()

    def _button_loop(self):
        """check the button state and handle it"""
        self.button.run()
        while self._keep_running:
            time.sleep(0.1)
            # print(".", end="")
            if self.button.is_pressed_now():
                self.log.debug("Button pressed now")
                # self.log.debug(f"Button timer: {self.button._press_timer.timer()}")
            if self.button.has_been_pressed_long_enough():
                press_timestamp = time.time()
                # for some reason the CubeMaster doesn't get the messages when it's sent to its ip.
                # might be beause everyone is on 192.168.1.0, I don't know. For now, let's just use
                # the broadcast address.
                # if self.net.send_msg_to_cubeserver(cm.CubeMsgButtonPress(self.net.node_name)):
                cbp_msg = cm.CubeMsgButtonPress(sender=self.net.node_name,
                                                start_timestamp=self.play_start_timestamp,
                                                press_timestamp=press_timestamp)
                self.log.info(f"Button pressed long enough. Sending msg to CubeMaster : {cbp_msg.to_string()}")

                if self.net.send_msg_to_cubeserver(cbp_msg, require_ack=True):
                    self.log.info("Button press message sent to and acked by CubeMaster")
                    self.badge_out_current_team()
                    self.set_as_not_playing()
                    self.buzzer.play_victory_sound()

                else:
                    self.log.error("Failed to send or get ack for button press message to CubeMaster")
                self.button.reset()
                self.button.wait_until_released()
                self.log.info("Button released")
                self.button.reset()
                self.log.info("Button reset")
        self.button.stop()


if __name__ == "__main__":
    import atexit

    box = CubeServerCubebox("CubeBox1")
    atexit.register(box.stop)
    try:
        box.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping CubeBox...")
        box.stop()
