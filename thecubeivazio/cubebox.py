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

print("cube logger contents:")
print(dir(cube_logger))



# TODO: put rfid, button, and networking in separate threads
class CubeBox:
    def __init__(self, node_name: str):
        self.log = cube_logger.make_logger(name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.net = cubenet.CubeNetworking(node_name=node_name, log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.net.ACK_NB_TRIES = 999
        # self.net.UDP_PORT = 5000 + self.get_cubebox_index()
        self.rfid = cube_rfid.CubeRfidListener()
        self.button = cube_button.CubeButton()
        self.buzzer = cube_buzzer.CubeBuzzer()

        self.heartbeat_timer = cube_utils.SimpleTimer(10)
        self.enable_heartbeat = False

        self._thread_rfid = None
        self._thread_button = None
        self._thread_networking = None

        self._keep_running = False

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
        # initial heartbeat to signal one's presence and identity
        self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
        self.heartbeat_timer.reset()


    def stop(self):
        """Stop the RFID, button, and networking threads"""
        self._keep_running = False
        self._thread_rfid.join()
        self._thread_button.join()
        self._thread_networking.join()

    def _networking_loop(self):
        """check the incoming messages and handle them"""
        self.net.run()
        while self._keep_running:
            time.sleep(0.1)
            if self.enable_heartbeat and self.heartbeat_timer.is_timeout():
                self.net.send_msg_with_udp(cm.CubeMsgHeartbeat(self.net.node_name))
                self.heartbeat_timer.reset()

            for message in self.net.get_incoming_msg_queue():
                # if message.msgtype == cm.CubeMsgType.VERSION_REQUEST:
                #     self.net.send_msg_with_udp(cm.CubeMsgVersionReply(self.net.node_name))
                # TODO: handle other message types
                pass
        self.net.stop()

    def _rfid_loop(self):
        """check the RFID lines and handle them"""
        self.rfid.run()
        while self._keep_running:
            time.sleep(0.1)
            for line in self.rfid.get_completed_lines():
                print(f"Line entered at {line.timestamp}: {line.uid} : {'valid' if line.is_valid() else 'invalid'}")
                if line.is_valid():
                    # for some reason the CubeServer doesn't get the messages when it's sent to its ip.
                    # might be beause everyone is on 192.168.1.0, I don't know. For now, let's just use
                    # the broadcast address.
                    #result = self.net.send_msg_to_cubeserver(cm.CubeMsgRfidRead(self.net.node_name, uid=line.uid, timestamp=line.timestamp))
                    result = self.net.send_msg_with_udp(cm.CubeMsgRfidRead(self.net.node_name, uid=line.uid, timestamp=line.timestamp))
                    if not result:
                        self.log.error("Failed to send RFID read message to CubeServer")
                        self.buzzer.play_rfid_error_sound()
                    else:
                        self.log.info("RFID read message sent to CubeServer")
                        self.buzzer.play_rfid_ok_sound()
                        self.rfid.remove_line(line)
        self.rfid.stop()

    def _button_loop(self):
        """check the button state and handle it"""
        self.button.run()
        while self._keep_running:
            time.sleep(0.1)
            #print(".", end="")
            if self.button.is_pressed_now():
                self.log.debug("Button pressed now")
                #self.log.debug(f"Button timer: {self.button._press_timer.timer()}")
            if self.button.has_been_pressed_long_enough():
                self.log.info("Button pressed long enough. Sending msg to CubeServer")
                # for some reason the CubeServer doesn't get the messages when it's sent to its ip.
                # might be beause everyone is on 192.168.1.0, I don't know. For now, let's just use
                # the broadcast address.
                #if self.net.send_msg_to_cubeserver(cm.CubeMsgButtonPress(self.net.node_name)):
                if self.net.send_msg_with_udp(cm.CubeMsgButtonPress(self.net.node_name)):
                    self.buzzer.play_victory_sound()
                else:
                    self.log.error("Failed to send button press message to CubeServer")
                self.button.wait_until_released()
                self.log.info("Button released")
                self.button.reset()
                self.log.info("Button reset")
        self.button.stop()



if __name__ == "__main__":
    import atexit

    box = CubeBox("CubeBox1")
    atexit.register(box.stop)
    try:
        box.run()
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping CubeBox...")
        box.stop()
