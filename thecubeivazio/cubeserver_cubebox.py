"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""
import threading
import time

import thecubeivazio.cube_button as cube_button
import thecubeivazio.cube_identification as cubeid
import thecubeivazio.cube_logger as cube_logger
import thecubeivazio.cube_messages as cm
import thecubeivazio.cube_networking as cubenet
import thecubeivazio.cube_rfid as cube_rfid
import thecubeivazio.cube_sounds as cube_sounds
import thecubeivazio.cube_utils as cube_utils
import thecubeivazio.cube_config as cube_config
import thecubeivazio.cube_game as cube_game
import thecubeivazio.cube_neopixel as cube_neopixel
from thecubeivazio.cube_common_defines import *


class CubeServerCubebox:
    def __init__(self, cube_id: int = 1):
        node_name = cubeid.cubebox_index_to_node_name(cube_id)
        if not node_name:
            node_name = self._determine_cubebox_node_name()

        self.log = cube_logger.CubeLogger(name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.log.setLevel(cube_logger.logging.INFO)
        self.log.info("Starting CubeServerCubebox...")

        # create a config object which we'll use to access the config file's contents
        # and keep it updated with possible changes from the frontdesk
        self.config = cube_config.CubeConfig.get_config()

        # set up the networking module
        self.net = cubenet.CubeNetworking(node_name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        # number of tries for the ACK messages. We can afford to set it a bit higher for the cubeboxes
        # because they're not as central and busy as the CubeMaster of the CubeFrontdesk
        self.net.ACK_NB_TRIES = 10

        # if the node name is not a valid cubebox name, send an alert to all and raise an error.
        # this should NEVER happen, but if it does, we must know about it
        if not node_name in cubeid.CUBEBOXES_NODENAMES:
            self.net.send_msg_to_all(cm.CubeMsgAlert(sender=self.net.node_name,
                                                     alert=f"Invalid node name: {node_name}"),
                                        require_ack=False)
            self.log.error(f"Invalid node name: {node_name}")
            raise ValueError(f"Invalid node name: {node_name}")

        # keeps tracks of the game's status for this cubebox.
        # meant to be set only with the set_status_state method
        self._status = cube_game.CubeboxStatus(cube_id=self.cubebox_index)

        # handles the wireless button presses
        self.button = cube_button.CubeButton()

        # handles sound playing
        self.sound_player = cube_sounds.CubeSoundPlayer(init_timeout_sec=5)
        self.sound_player.wait_for_mixer_initialized(timeout_sec=5)
        self.sound_player.set_volume_percent(self.config.cubebox_audio_volume_percent)

        # the neopixel ring light for the rfid reader
        self.neopixel = cube_neopixel.CubeNeopixel()

        # RFID handler, set up with self._rfid_setup_loop()
        self.rfid: cube_rfid.CubeRfidListenerBase = None
        # try to set up the RFID listener until it's done.
        # It's important to make sure it's set up and it's one of the most failure-prone parts of the code
        self._rfid_setup_loop()

        # NOTE: we're not using the heartbeat timer but hey,
        # it doesn't hurt to have it ready in case I change my mind.
        # when enabled, sends a heartbeat message periodically
        self.heartbeat_timer = cube_utils.CubeSimpleTimer(10)
        self.enable_heartbeat = False

        # the threads to run the different loops
        self._thread_rfid = threading.Thread(target=self._rfid_loop, daemon=True)
        self._thread_button = threading.Thread(target=self._button_loop, daemon=True)
        self._thread_networking = threading.Thread(target=self._message_handling_loop, daemon=True)
        # flag to keep the threads loops running or stop them
        self._keep_running = False

        # at startup, a cubebox is ready to play by default
        self.set_status_state(cube_game.CubeboxState.STATE_READY_TO_PLAY)

        # notify the people around that the cubebox has booted and is ready
        self.sound_player.play_startup_sound()

        self.log.success("CubeServerCubebox started.")

    @property
    def status(self) -> cube_game.CubeboxStatus:
        return self._status

    @property
    def node_name(self) -> str:
        return self.net.node_name

    @cubetry
    def set_status_state(self, state: cube_game.CubeboxState):
        self.log.info(f"Setting the status to {state}")
        if self._status.set_state(state):
            self.send_status_to_all()
        if self._status.get_state() == cube_game.CubeboxState.STATE_WAITING_FOR_RESET:
            self.neopixel.set_hue_wait_for_reset()
        elif self._status.get_state() == cube_game.CubeboxState.STATE_READY_TO_PLAY:
            self.neopixel.set_hue_ready_to_play()
        elif self._status.get_state() == cube_game.CubeboxState.STATE_PLAYING:
            self.neopixel.set_hue_currently_playing()
        else:
            self.neopixel.set_hue_error()
            self.log.error(f"Unknown state: {state}")
        self.log.debug(f"Set the neopixel to {self.neopixel.color}")

    @cubetry
    def send_status_to_all(self):
        """notifies everyone about the current status of this cubebox instance"""
        self.net.send_msg_to_all(
            cm.CubeMsgReplyCubeboxStatus(self.net.node_name, self.status),
            require_ack=False)

    @cubetry
    def _determine_cubebox_node_name(self) -> str:
        """determine the node name from the hostname"""
        return cubeid.hostname_to_valid_cubebox_name()

    @cubetry
    def _handle_config_message(self, message: cm.CubeMessage):
        self.log.info(f"Received config message from {message.sender}")
        config_msg = cm.CubeMsgConfig(copy_msg=message)
        self.log.info(f"Config message: {config_msg.to_string()}")
        self.config.update_from_config(config_msg.config)
        self.config.save_to_json_file()
        self.log.success("Config updated and saved.")
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
        # adjust the volume of the sound player
        self.sound_player.set_volume_percent(self.config.cubebox_audio_volume_percent)

    @cubetry
    def _handle_command_message(self, message: cm.CubeMessage) -> bool:
        self.log.info(f"Received command message from {message.sender}")
        command_msg = cm.CubeMsgCommand(copy_msg=message)
        self.log.info(f"Command message: {command_msg.to_string()}")
        command = command_msg.command_without_target
        target = command_msg.target
        if target not in (self.net.node_name, cubeid.EVERYONE_NODENAME):
            self.log.info(f"Command target not for me: {target}")
            return False
        if not self.handle_command(command):
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)
            return False
        self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
        return True

    @cubetry
    def handle_command(self, command: str) -> bool:
        self.log.info(f"Handling command: '{command}'")
        words = [x.strip() for x in command.split()]
        cmd = words[0]
        arg1 = words[1] if len(words) > 1 else None
        if cmd == "reset":
            self.perform_reset()
            return True
        elif cmd == "reboot":
            cube_utils.reboot()
            return True
        elif cmd == "button":
            self.simulate_button_long_press()
            return True
        elif cmd == "rfid" and arg1 is not None:
            self.simulate_rfid_read(arg1)
            return True
        elif cmd == "test_sound":
            self.sound_player.play_startup_sound()
            return True
        else:
            self.log.error(f"Unknown command: {cmd}")
            return False

    @cubetry
    def simulate_rfid_read(self, uid: str):
        self.rfid.simulate_read(uid)

    @cubetry
    def simulate_button_long_press(self):
        self.button.simulate_long_press()

    @property
    def cubebox_index(self):
        return cubeid.node_name_to_cubebox_index(self.net.node_name)

    @cubetry
    def is_box_being_played(self):
        return self.status.is_playing()

    @cubetry
    def to_string(self):
        ret = f"CubeServerCubebox({self.net.node_name})\n"
        ret += f"- last_rfid_line: {self.status.last_valid_rfid_line}\n"
        ret += f"- Status: {self.status}\n"
        return ret

    def __repr__(self):
        return self.to_string()

    def __str__(self):
        return self.to_string()

    @property
    def play_start_timestamp(self) -> Optional[Seconds]:
        # noinspection PyBroadException
        try:
            return self.status.last_valid_rfid_line.timestamp
        except:
            return None

    def run(self):
        """Start the RFID, button, and networking threads"""
        self._thread_rfid = threading.Thread(target=self._rfid_loop, daemon=True)
        self._thread_button = threading.Thread(target=self._button_loop, daemon=True)
        self._thread_networking = threading.Thread(target=self._message_handling_loop, daemon=True)
        self._keep_running = True
        self._thread_rfid.start()
        self._thread_button.start()
        self._thread_networking.start()

    def stop(self):
        """Stop the RFID, button, and networking threads"""
        try:
            self._keep_running = False
            self._thread_button.join(timeout=0.1)
            self._thread_networking.join(timeout=0.1)
            self._thread_rfid.join(timeout=0.1)
            self.log.info("Stopped the CubeServerCubebox")
        except Exception as e:
            self.log.error(f"Error stopping threads: {e}")



    def _message_handling_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            for message in self.net.get_incoming_msg_queue():
                # ignore ack messages, they're handled in the networking module
                if message.msgtype == cm.CubeMsgTypes.ACK:
                    continue
                elif message.msgtype == cm.CubeMsgTypes.COMMAND:
                    self._handle_command_message(message)
                elif message.msgtype == cm.CubeMsgTypes.CONFIG:
                    self._handle_config_message(message)
                elif message.msgtype == cm.CubeMsgTypes.ORDER_CUBEBOX_TEAM_BADGE_OUT:
                    self._handle_order_team_badge_out_message(message)
                elif message.msgtype == cm.CubeMsgTypes.ORDER_CUBEBOX_TO_WAIT_FOR_RESET:
                    self._handle_order_cubebox_to_wait_for_reset_message(message)
                elif message.msgtype == cm.CubeMsgTypes.ORDER_CUBEBOX_TO_RESET:
                    self._handle_order_cubebox_to_reset_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_ALL_CUBEBOXES_STATUSES:
                    self._handle_request_all_cubeboxes_statuses_message(message)
                elif message.msgtype == cm.CubeMsgTypes.REQUEST_CUBEBOX_STATUS:
                    self._handle_request_cubebox_status_message(message)
                else:
                    self.log.debug(f"Unhandled message: {message}")
                self.net.remove_msg_from_incoming_queue(message)

    def _handle_order_team_badge_out_message(self, message: cm.CubeMessage) -> bool:
        self.log.info("Received order to badge out a team")
        otbo_msg = cm.CubeMsgOrderCubeboxTeamBadgeOut(copy_msg=message)
        try:
            cube_id = otbo_msg.cube_id
            team_name = otbo_msg.team_name
            assert cube_id == self.cubebox_index
            self.badge_out_current_team()
            self.log.success(f"Team {team_name} badged out")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.OK)
            return True
        except Exception as e:
            self.log.error(f"Error handling order to badge out a team: {e}")
            self.net.acknowledge_this_message(message, cm.CubeAckInfos.ERROR)
            return False

    @cubetry
    def _handle_order_cubebox_to_reset_message(self, message: cm.CubeMessage) -> bool:
        octr_msg = cm.CubeMsgOrderCubeboxToReset(copy_msg=message)
        if octr_msg.cube_id != self.cubebox_index:
            return True
        self.log.info("Received order to reset")
        self.perform_reset()
        self.net.send_msg_to_all(cm.CubeMsgReplyCubeboxStatus(self.net.node_name, self.status))
        return True

    @cubetry
    def _handle_order_cubebox_to_wait_for_reset_message(self, message: cm.CubeMessage) -> bool:
        octwfr_msg = cm.CubeMsgOrderCubeboxToWaitForReset(copy_msg=message)
        if octwfr_msg.cube_id != self.cubebox_index:
            return True
        self.log.info("Received order to wait for reset")
        self.badge_out_current_team()
        self.set_status_state(cube_game.CubeboxState.STATE_WAITING_FOR_RESET)
        return True

    @cubetry
    def perform_reset(self):
        self.set_status_state(cube_game.CubeboxState.STATE_READY_TO_PLAY)
        self.sound_player.play_cubebox_reset_sound()

    @cubetry
    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        try:
            assert self.rfid.is_setup()
        except AssertionError:
            self._rfid_setup_loop()
        self.rfid.run()
        while self._keep_running:
            time.sleep(LOOP_PERIOD_SEC)
            # if the rfid gets disconnected, try to set it up again
            if not self.rfid.is_setup():
                self._rfid_setup_loop()
                self.rfid.run()
                continue
            for rfid_line in self.rfid.get_completed_lines():
                rfid_line: cube_rfid.CubeRfidLine
                self.log.info(
                    f"Line entered at {rfid_line.timestamp}: {rfid_line.uid} : {'valid' if rfid_line.is_valid() else 'invalid'}")
                self.log.critical(f"Resetters: {cube_rfid.CubeRfidLine.get_resetter_uids_list()}")
                if not rfid_line.is_valid():
                    self.rfid.remove_line(rfid_line)
                    self.sound_player.play_rfid_error_sound()
                # if this rfid uid is in the resetter list, set the box status to ready to play
                elif cube_rfid.CubeRfidLine.is_uid_in_resetter_list(rfid_line.uid):
                    self.log.info(
                        f"RFID {rfid_line.uid} is in the resetter list. Setting the box status to ready to play.")
                    self.perform_reset()
                # ok, so the line is valid and it's not a resetter rfid, which means it's a team rfid.
                # if the box is not ready to play, ignore the read
                elif not self.status.is_ready_to_play():
                    self.log.warning("Trying to badge in a team but the box is not ready to play")
                    self.sound_player.play_rfid_error_sound()
                # if we're here. that means the box is ready to play. badge in the new team
                else:
                    self.badge_in_new_team(rfid_line)
                # finally, in any case, remove the line from the rfid listener
                self.rfid.remove_line(rfid_line)

    @cubetry
    def _rfid_setup_loop(self) -> bool:
        """while the rfid is not setup, try to set it up, first as a serial listener, then as a keyboard listener"""
        self.neopixel.set_hue(cube_neopixel.CubeNeopixel.HUE_ERROR)
        while True:
            self.log.info("RFID not setup. Trying to set it up...")
            self.rfid = cube_rfid.CubeRfidSerialListener()
            self.log.info("Trying to set up RFID as a serial listener...")
            if self.rfid.is_setup():
                self.log.success("RFID set up as a serial listener")
                break
            self.log.warning("Failed to set up RFID as a serial listener. Trying event listener...")
            self.log.info("Trying to set up RFID as an event listener...")
            self.rfid = cube_rfid.CubeRfidEventListener(show_debug=True)
            if self.rfid.is_setup():
                self.log.success("RFID set up as an event listener")
                break
            self.log.error("Failed to set up RFID listener. Trying again in 3 seconds...")
            time.sleep(3)
        self.set_status_state(self._status.get_state())
        return True

    @cubetry
    def badge_in_new_team(self, rfid_line: cube_rfid.CubeRfidLine) -> bool:
        if cube_rfid.CubeRfidLine.is_uid_in_resetter_list(rfid_line.uid):
            self.log.warning(f"Trying to badge in a team with a resetter RFID {rfid_line.uid}")
            self.perform_reset()
            return False

        self.log.info(f"Checking before badging in team with RFID {rfid_line.uid}...")
        if not rfid_line.is_valid():
            self.log.error("Trying to badge in an invalid RFID line")
            self.sound_player.play_rfid_error_sound()
            return False
        if not self.status.is_ready_to_play():
            self.log.warning("Trying to badge in a team but the box is not ready to play")
            self.sound_player.play_rfid_error_sound()
            return False
        # alright so it's a valid line. let's add it to our status
        self.status.last_valid_rfid_line = rfid_line
        # send the RFID read message to the CubeMaster
        msg_rr = cm.CubeMsgRfidRead(self.net.node_name, uid=rfid_line.uid, timestamp=rfid_line.timestamp)
        report = self.net.send_msg_to_cubemaster(msg_rr, require_ack=True, nb_tries=3)
        if not report.sent_ok:
            self.log.error("Failed to send RFID read message to CubeMaster")
            self.sound_player.play_rfid_error_sound()
            return False
        if not report.ack_msg:
            self.log.error("Sent RFID messages but the CubeMaster did not acknowledge it")
            self.sound_player.play_rfid_error_sound()
            return False
        if report.ack_info != cm.CubeAckInfos.OK:
            self.log.error(f"CubeMaster acked the RFID read message with error: {report.ack_info}")
            self.sound_player.play_rfid_error_sound()
            return False
        else:
            self.log.success("RFID read message sent to and okayed by the CubeMaster")
            self.status.last_valid_rfid_line = rfid_line
            self.set_status_state(cube_game.CubeboxState.STATE_PLAYING)
            self.log.info(
                f"is_box_being_played()={self.is_box_being_played()}, last_rfid_line={self.status.last_valid_rfid_line}")
            # self.log.critical(f"{self.status}")
            self.sound_player.play_rfid_ok_sound()
            return True

    @cubetry
    def badge_out_current_team(self, play_game_over_sound=False) -> bool:
        if self.status.last_valid_rfid_line is None:
            self.log.warning("Trying to badge out a team but there is no team to badge out")
        else:
            self.log.info(f"Badging out team with RFID {self.status.last_valid_rfid_line.uid}")
            if play_game_over_sound:
                self.sound_player.play_game_over_sound()
        self.set_status_state(cube_game.CubeboxState.STATE_WAITING_FOR_RESET)
        return True

    @cubetry
    def _button_loop(self):
        """check the button state and handle it"""
        self.button.run()
        while self._keep_running:
            time.sleep(0.1)

            # print(".", end="")
            # if self.button.is_pressed_now():
            # self.log.debug("Button pressed now")
            # self.log.debug(f"Button timer: {self.button._press_timer.timer()}")

            if not self.button.has_been_pressed_long_enough():
                continue
            # if we're here. it means we've got a long press
            if not self.is_box_being_played():
                self.log.warning("The button was pressed long enough but the box is not being played. Ignoring.")
                self.button.reset()
                continue
            press_timestamp = time.time()

            cbp_msg = cm.CubeMsgButtonPress(sender=self.net.node_name,
                                            start_timestamp=self.play_start_timestamp,
                                            press_timestamp=press_timestamp)
            self.log.info(f"Button pressed long enough. Sending msg to CubeMaster : {cbp_msg.to_string()}")

            if self.net.send_msg_to_cubemaster(cbp_msg, require_ack=True):
                self.log.info("Button press message sent to and acked by CubeMaster")
                self.badge_out_current_team()
                self.set_status_state(cube_game.CubeboxState.STATE_WAITING_FOR_RESET)
                self.sound_player.play_victory_sound()
            else:
                self.log.error("Failed to send or get ack for button press message to CubeMaster")
            self.button.reset()
            self.button.wait_until_released()
            self.log.info("Button released")
            self.button.reset()
            self.log.info("Button reset")
        self.button.stop()

    @cubetry
    def _handle_request_all_cubeboxes_statuses_message(self, message: cm.CubeMessage) -> bool:
        self.log.info("Received request for all cubeboxes statuses")
        report = self.net.send_msg_to(
            cm.CubeMsgReplyCubeboxStatus(self.net.node_name, self.status),
            node_name=message.sender,
            require_ack=False)
        return report.sent_ok

    @cubetry
    def _handle_request_cubebox_status_message(self, message: cm.CubeMessage) -> bool:
        rcs_msg = cm.CubeMsgRequestCubeboxStatus(copy_msg=message)
        if rcs_msg.cube_id != self.cubebox_index:
            return True
        self.log.info("Received request for cubebox status and it's for us")
        report = self.net.send_msg_to(
            cm.CubeMsgReplyCubeboxStatus(self.net.node_name, self.status),
            node_name=rcs_msg.sender,
            require_ack=False)
        return report.sent_ok


def main():
    import atexit
    box = CubeServerCubebox(1)
    atexit.register(box.stop)

    box.log.setLevel(cube_logger.logging.INFO)
    box.net.log.setLevel(cube_logger.logging.INFO)

    try:
        box.run()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping CubeBox...")
        box.stop()


def test_functionalities():
    """Tests all functionalities of the CubeServerCubebox class,
    call all methods (for handling methods, create dummy messages), even the private ones"""
    box = CubeServerCubebox(1)
    print(box)
    print(box.status)
    print(box.is_box_being_played())
    print(box.play_start_timestamp)
    print(box.cubebox_index)
    print(box.node_name)
    print(box.to_string())
    print(box.handle_command("reset"))
    print(box.handle_command("reboot"))
    print(box.handle_command("button"))
    print(box.handle_command("rfid 1234567800"))
    print(box.badge_out_current_team())
    print(box.badge_out_current_team(play_game_over_sound=True))
    box.simulate_button_long_press()
    box.simulate_rfid_read("1234567890")



def test():
    import atexit
    box = CubeServerCubebox(1)
    atexit.register(box.stop)
    box.log.setLevel(cube_logger.logging.DEBUG)
    box.net.log.setLevel(cube_logger.logging.INFO)
    try:
        box.run()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping CubeBox...")
        box.stop()


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        test()
    else:
        main()
