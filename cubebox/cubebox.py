"""
The CubeBox module handles everything in CubeBoxes, i.e. the raspberrypis embedded within TheCube's boxes
"""
import cube_logger
import cube_rfid
import cubebox_button
import cube_networking as cubenet
import cube_messages as cm
import cube_utils


class CubeBox:
    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(node_name)
        self.net = cubenet.CubeNetworking(node_name=node_name)
        self.rfid = cube_rfid.CubeRfidListener()
        self.button = cubebox_button.CubeBoxButton()
        self.heartbeat_timer = cube_utils.SimpleTimer(10)

    def run(self):
        self.net.run()
        self.rfid.run()
        self.button.run()
        while True:
            self.handle_networking()
            self.handle_rfid()
            self.handle_button()

    def stop(self):
        self.net.stop()
        self.rfid.stop()
        self.button.stop()

    def handle_networking(self):
        """check the incoming messages and handle them"""
        if self.heartbeat_timer.is_timeout():
            self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
            self.heartbeat_timer.reset()

        for message in self.net.get_incoming_msg_queue():
            if message.msgtype == cm.CubeMsgType.VERSION_REQUEST:
                self.net.send_msg_with_udp(cm.CubeMsgVersionReply(self.net.node_name))
            # TODO: handle other message types


    def handle_rfid(self):
        """check the RFID lines and handle them"""
        for line in self.rfid.get_completed_lines():
            print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
            if line.is_valid():
                result = self.net.send_msg_to_cubeserver(
                    cm.CubeMsgRfidRead(self.net.node_name, uid=line.uid, timestamp=line.timestamp))
                if not result:
                    self.log.error("Failed to send RFID read message to CubeServer")
                    self.play_rfid_error_sound()
                else:
                    self.log.info("RFID read message sent to CubeServer")
                    self.play_rfid_ok_sound()
                    self.rfid.remove_line(line)

    def handle_button(self):
        """check the button state and handle it"""
        if self.button.has_been_pressed_long_enough():
            self.log.info("Button pressed long enough")
            self.button.reset()
            self.play_victory_sound()


    def play_rfid_ok_sound(self):
        # TODO
        self.log.info("Playing RFID OK sound")

    def play_rfid_error_sound(self):
        # TODO
        self.log.error("Playing RFID error sound")

    def play_victory_sound(self):
        # TODO
        self.log.info("Playing victory sound")

    def play_game_over_sound(self):
        # TODO
        self.log.info("Playing game over sound")


if __name__ == "__main__":
    import atexit
    box = CubeBox("CubeBox1")
    atexit.register(box.stop)
    box.run()
