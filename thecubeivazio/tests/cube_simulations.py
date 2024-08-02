import logging
import random
import re
import threading
import time
from typing import Callable

from thecubeivazio import cube_game as cgame, cube_game as cube_game
from thecubeivazio import cube_identification as cid
from thecubeivazio import cube_logger
from thecubeivazio.cube_neopixel import CubeNeopixel
from thecubeivazio.cubeserver_cubebox import CubeServerCubebox
from thecubeivazio.cubeserver_frontdesk import CubeServerFrontdesk
from thecubeivazio.cubeserver_cubemaster import CubeServerMaster
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_rfid import CubeRfidLine
from thecubeivazio import cube_database as cubedb
from thecubeivazio import cube_networking as cubenet


def extract_first_argument(source):
    # Use regex to extract the first argument of the function call
    match = re.search(r'\((.*)\)', source)
    if match:
        return match.group(1).strip()
    return source.strip()

def extract_function_source(func):
    # Use regex to extract the function call
    source = inspect.getsource(func).strip()
    match = re.search(r'def\s+(\w+)', source)
    if match:
        return f"{match.group(1)}()"
    return source

def extract_lambda_source(source):
    # Use regex to extract the body of the lambda function
    match = re.search(r'lambda\s*:\s*(.*)', source)
    if match:
        return match.group(1).strip()
    return source.strip()

def split_by_comma_outside_parentheses(s):
    """
    Split the string by the comma that is outside of any parentheses.
    """
    parts = []
    part = []
    depth = 0
    for char in s:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            parts.append(''.join(part).strip())
            part = []
            continue
        part.append(char)
    parts.append(''.join(part).strip())
    return parts

class TestResults:
    RESULT_PASS = "PASS"
    RESULT_FAIL = "FAIL"

    def __init__(self):
        self.statements = []
        self.results = []
        self.info = None

    def add(self, statement, result, info=None):
        self.statements.append(statement)
        self.results.append(result)
        self.info = info


def get_random_resetter_uid():
    resetters = CubeRfidLine.get_resetter_uids_list()[0]
    return random.choice(resetters)


class CubeBoxRemoteInterface(CubeServerCubebox):
    def __init__(self, cube_id:CubeId, frontdesk:CubeServerFrontdesk, update_timeout_sec:float=3):
        # super().__init__(cube_id=cube_id)
        self.cube_id = cube_id

        self.log = cube_logger.CubeLogger(name=f"Remote {self.node_name}", log_filename=cube_logger.CUBEBOX_LOG_FILENAME)
        self.log.setLevel(cube_logger.logging.INFO)

        self._frontdesk = frontdesk
        self.cube_id = cube_id
        self._update_timeout_sec = update_timeout_sec
        super().stop()
        self.log.info("Remote cubebox created")

    @property
    def node_name(self):
        return cid.cubebox_index_to_node_name(self.cube_id)

    @cubetry
    def update_status(self) -> bool:
        return self._frontdesk.request_cubebox_status(
            cubebox_id=self.cube_id, timeout=self._update_timeout_sec)

    @property
    def status(self) -> Optional[cgame.CubeboxStatus]:
        try:
            assert self.update_status()
            return self._frontdesk.cubeboxes.get_cubebox_by_cube_id(self.cube_id)
        except Exception as e:
            self.log.error(f"Error updating cubebox status: {e}")
            return None

    def set_status_state(self, state: cube_game.CubeboxState):
        pass

    def run(self):
        pass

    def stop(self):
        self._frontdesk.send_full_command(f"{self.node_name} reset")

    def simulate_rfid_read(self, uid: str):
        self._frontdesk.send_full_command(f"{self.node_name} rfid {uid}")

    def simulate_button_long_press(self):
        self._frontdesk.send_full_command(f"{self.node_name} button")



class CubeMasterRemoteInterface(CubeServerMaster):
    # noinspection PyMissingConstructor
    def __init__(self, frontdesk:CubeServerFrontdesk, update_timeout_sec:float=5):
        # super().__init__()
        self.node_name = cid.CUBEMASTER_NODENAME

        self.log = cube_logger.CubeLogger(name=f"Remote {self.node_name}", log_filename=cube_logger.CUBEMASTER_LOG_FILENAME)
        self.log.setLevel(cube_logger.logging.INFO)
        # self.net = cubenet.CubeNetworking(self.node_name, None)
        # self.net.stop()

        self._frontdesk = frontdesk
        self._update_timeout_sec = update_timeout_sec

        # setup the local database
        self.database = cubedb.CubeDatabase(CUBEMASTER_SQLITE_DATABASE_FILEPATH)
        # if the play database does not exist, create it
        if not self.database.does_database_exist():
            self.database.create_database()
            self.log.info("Created the local database")

        # super().stop()
        self.log.info("Remote cubemaster created")

    @cubetry
    def update_status(self) -> bool:
        return self._frontdesk.request_cubemaster_status(reply_timeout=self._update_timeout_sec)

    @property
    def game_status(self) -> Optional[cgame.CubeGameStatus]:
        try:
            assert self.update_status()
            return self._frontdesk.game_status
        except Exception as e:
            self.log.error(f"Error updating cubemaster status: {e}")
            return None

    def run(self):
        # fresh start
        self.stop()

    def stop(self):
        self.log.critical(f"sending reset command. ack_timeout: {self._frontdesk.net.ACK_WAIT_TIMEOUT}")
        return self._frontdesk.send_full_command(f"{self.node_name} reset")


CubeSimBox = Union[CubeServerCubebox, CubeBoxRemoteInterface]
CubeSimBoxList = list[CubeSimBox]
CubeSimMaster = Union[CubeServerMaster, CubeMasterRemoteInterface]


class CubeTester:
    COMM_DELAY_SEC = 3


    def __init__(self, name="CubeTester", nb_cubeboxes=1):
        self.name = name
        self.log = cube_logger.CubeLogger(name)

        self.frontdesk = CubeServerFrontdesk()

        self.local_cubeboxes:list[CubeServerCubebox] = [CubeServerCubebox(i + 1) for i in range(nb_cubeboxes)]
        self.remote_cubeboxes:list[CubeBoxRemoteInterface] = [CubeBoxRemoteInterface(cube_id=i + 1, frontdesk=self.frontdesk) for i in range(nb_cubeboxes)]

        self.local_master = CubeServerMaster()
        self.remote_master = CubeMasterRemoteInterface(frontdesk=self.frontdesk)

        self.frontdesk_thread = threading.Thread(target=self.frontdesk.run, daemon=True)
        # noinspection PyTypeChecker
        self.cubebox_threads: list[threading.Thread] = [None] * nb_cubeboxes
        # noinspection PyTypeChecker
        self.master_thread: threading.Thread = None

        self.results = TestResults()
        # if this flag is False, the cubebox instances will be locally defined instances of CubeServerCubebox
        # if this flag is True, we expect that actual cubeboxes are running on the network.
        # The local instances used for testing will be updated with status replies from the cubeboxes,
        # triggered by requests from the (local) frontdesk.
        # see update_cubeboxes_statuses in this class for more details.
        self._common_start_done = False
        self.redo_common_start = True
        # put in this list the nodenames that will be tested remotely and not as local simulation instances
        self.remote_nodenames = []

    @property
    def possible_nodenames(self) -> list[cid.NodeName]:
        ret = [cid.CUBEMASTER_NODENAME]
        for i in range(self.nb_cubeboxes):
            ret.append(cid.cubebox_index_to_node_name(i + 1))
        return ret

    @property
    def local_nodenames(self):
        return [x for x in self.possible_nodenames if x not in self.remote_nodenames]

    def cubemaster_is_local(self):
        return cid.CUBEMASTER_NODENAME not in self.remote_nodenames

    def set_cubemaster_to_remote(self):
        if not cid.CUBEMASTER_NODENAME in self.remote_nodenames:
            self.remote_nodenames.append(cid.CUBEMASTER_NODENAME)

    def set_cubemaster_to_local(self):
        if cid.CUBEMASTER_NODENAME in self.remote_nodenames:
            self.remote_nodenames.remove(cid.CUBEMASTER_NODENAME)

    def set_every_node_to_local(self):
        self.remote_nodenames = []

    def set_every_node_to_remote(self):
        self.remote_nodenames = self.possible_nodenames

    def set_every_cubebox_to_local(self):
        if self.cubemaster_is_local():
            self.remote_nodenames = []
            self.set_cubemaster_to_local()
        else:
            self.remote_nodenames = []


    @property
    def master(self) -> CubeSimMaster:
        if self.cubemaster_is_local():
            return self.local_master
        else:
            return self.remote_master

    @property
    def cubeboxes(self) -> CubeSimBoxList:
        ret = []
        for nodename in cid.CUBEBOXES_NODENAMES:
            cubebox = None
            # if this cubebox is tested remotely, we're interested in the frontdesk's cubebox instances
            if nodename in self.remote_nodenames:
                cubebox = self.frontdesk.cubeboxes.get_cubebox_by_node_name(nodename)
            # if this cubebox is tested locally, we're interested in the local cubebox instances
            elif nodename in self.local_nodenames:
                self.log.critical(
                    f"cubeboxes property: nodename={nodename},"
                    f"len(local_cubeboxes)={len(self.local_cubeboxes)},")
                cubebox = [x for x in self.local_cubeboxes if x.node_name == nodename][0]
            if cubebox:
                ret.append(cubebox)
        return ret

    @property
    def nb_cubeboxes(self):
        return len(self.local_cubeboxes)

    @property
    def cubeboxes_ids(self) -> list[CubeId]:
        return [cubebox.cube_id for cubebox in self.cubeboxes]

    def common_start(self):
        """Common setup for the tests:
        - start the servers
        - set the log levels to INFO
        - disable the RFID listeners
        - use custom databases
        """
        if self._common_start_done and not self.redo_common_start:
            return
        if self._common_start_done and self.redo_common_start:
            self.stop_simulation()

        # start the threads
        for cube_id, cubebox_thread in enumerate(self.cubebox_threads):
            cubebox = self.cubeboxes[cube_id]
            cube_id += 1
            cubebox_thread = threading.Thread(target=cubebox.run, daemon=True)
            cubebox_thread.start()
        self.frontdesk_thread.start()
        self.master_thread = threading.Thread(target=self.master.run, daemon=True)
        self.master_thread.start()

        # set log levels
        for cubebox in self.local_cubeboxes:
            cubebox.log.setLevel(logging.INFO)
            cubebox.net.log.setLevel(logging.INFO)

        self.frontdesk.log.setLevel(logging.INFO)
        self.frontdesk.net.log.setLevel(logging.INFO)

        self.master.log.setLevel(logging.INFO)
        if self.cubemaster_is_local():
            self.master.net.log.setLevel(logging.INFO)

        # disable RFID listeners, we will simulate the RFID reads
        for cubebox in self.local_cubeboxes:
            cubebox.rfid.disable()
        if self.cubemaster_is_local():
            self.master.rfid.disable()
        self.frontdesk.rfid.disable()

        # use custom databases just for the simulation
        master_db_filename = os.path.join(SAVES_DIR, "master_test.db")
        frontdesk_db_filename = os.path.join(SAVES_DIR, "frontdesk_test.db")
        self.master.database = cubedb.CubeDatabase(master_db_filename)
        self.master.database.clear_database()
        self.frontdesk.database = cubedb.CubeDatabase(frontdesk_db_filename)
        self.frontdesk.database.clear_database()
        self._common_start_done = True

    def stop_simulation(self):
        try:
            self.log.info("Stopping the servers")
            for cubebox in self.cubeboxes:
                cubebox.stop()
            self.frontdesk.stop()
            self.master.stop()

            for cubebox_thread in self.cubebox_threads:
                if cubebox_thread and cubebox_thread.is_alive():
                    cubebox_thread.join(timeout=0.1)
            if self.frontdesk_thread.is_alive():
                self.frontdesk_thread.join(timeout=0.1)
            if self.master_thread and self.master_thread.is_alive():
                self.master_thread.join(timeout=0.1)
        except Exception as e:
            self.log.error(f"An error occurred while stopping the servers: {e}")
            traceback.print_exc()

    def display_results(self):
        nb_tests = len(self.results.statements)
        nb_pass = self.results.results.count(TestResults.RESULT_PASS)
        nb_fail = self.results.results.count(TestResults.RESULT_FAIL)
        self.log.info("\n--------------------\nTestResults:\n--------------------\n")
        for i, statement in enumerate(self.results.statements):
            if self.results.results[i] == TestResults.RESULT_PASS:
                # LOGGER.info(f"PASS : {statement}: {self.results[i]}")
                self.log.success(f"PASS : {statement}")
            else:
                # LOGGER.warning(f"FAIL : {statement}: {self.results[i]}")
                self.log.critical(f"FAIL : {statement}")
        # display the failed tests
        self.log.critical("\n--------------------\nFailed tests:\n--------------------\n")
        if nb_fail == 0:
            self.log.success("No failed tests, yay \\o/")
        for i, statement in enumerate(self.results.statements):
            if self.results.results[i] == TestResults.RESULT_FAIL:
                self.log.critical(f"FAIL : {statement}")
        self.log.info(f"Results: {nb_pass}/{nb_tests} passed, {nb_fail}/{nb_tests} failed")

    def test(self, statement: Callable, description: str = None, dont_record=False) -> bool:
        statement_str = inspect.getsource(statement).strip()
        result = TestResults.RESULT_PASS
        log_in_real_time = True
        try:
            if not statement():
                result = TestResults.RESULT_FAIL
            else:
                result = TestResults.RESULT_PASS
        except Exception as e:
            if not dont_record:
                self.log.error(f"Exception while testing {statement_str}: {e}")
                traceback.print_exc()
                result = f"FAIL : {e}"
        finally:
            if not dont_record:
                self.results.add(statement_str, result)
                if log_in_real_time:
                    if result == TestResults.RESULT_FAIL:
                        self.log.critical(f"FAIL : {statement_str} : {description}")
                    else:
                        self.log.debug(f"PASS : {statement_str} : {description}")
            return result == TestResults.RESULT_PASS

    def test_neq(self, a, b, description: str = None) -> bool:
        if callable(a):
            statement_str = inspect.getsource(a).strip()
        else:
            statement_str = f"{a} == {b}"

        a_val = a() if callable(a) else a
        b_val = b() if callable(b) else b
        a_str = f"{a_val}"
        b_str = f"{b_val}"

        if a_val == b_val:
            self.log.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
            self.results.add(statement_str, self.results.RESULT_FAIL)
            return True
        else:
            self.log.debug(f"PASS : {statement_str} : {description}")
            self.results.add(statement_str, self.results.RESULT_PASS)
            return False

    def test_eq(self, a, b, description: str = None) -> bool:
        if callable(a):
            statement_str = inspect.getsource(a).strip()
        else:
            statement_str = f"{a} == {b}"

        a_val = a() if callable(a) else a
        b_val = b() if callable(b) else b
        a_str = f"{a_val}"
        b_str = f"{b_val}"

        if a_val != b_val:
            self.log.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
            self.results.add(statement_str, self.results.RESULT_FAIL)
            return True
        else:
            self.log.debug(f"PASS : {statement_str} : {description}")
            self.results.add(statement_str, self.results.RESULT_PASS)
            return False

    def wait(self, seconds, message: str = None):
        if message is not None:
            self.log.info(f"sleeping for {seconds}s : {message}")
        else:
            self.log.info(f"sleeping for {seconds}s")
        time.sleep(seconds)

    def wait_until(self, condition: Callable, timeout=5, message: str = None):
        start_time = time.time()
        if message is None:
            message = inspect.getsource(condition).strip()
        self.log.info(f"sleeping for {timeout}s max : {message}")
        try:
            while time.time() - start_time < timeout:
                if condition():
                    return
                time.sleep(0.1)
            self.log.warning(f"Timeout of {timeout}s reached while waiting for '{message}'")
        except Exception as e:
            self.log.error(f"An error occurred while waiting for '{condition}': {e}")
            traceback.print_exc()

    def partial_test_create_new_team(self, team:cgame.CubeTeamStatus):
        """A common test to create a new team on the frontdesk and check:
        - that the team is added to the master
        - that the team is correctly configured master-side (no cubebox associated, no completed cubeboxes)
        - that the team is correctly configured frontdesk-side (same as master)
        """
        team_name = team.name
        self.frontdesk.add_new_team(team)
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name) is not None,
                        message="waiting for the team to be added to the master",
                        timeout=self.COMM_DELAY_SEC)
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, None,
                     "Team should not be associated with a cubebox")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).completed_cubebox_ids, [],
                     "Team should not have completed any cubeboxes")
        self.test_eq(lambda: self.frontdesk.teams.get_team_by_name(team_name).current_cubebox_id, None,
                        "Team should not be associated with a cubebox")
        self.test_eq(lambda: self.frontdesk.teams.get_team_by_name(team_name).completed_cubebox_ids, [],
                        "Team should not have completed any cubeboxes")

    def partial_test_badge_team_in_cubebox(self, team:cgame.CubeTeamStatus, cubebox:CubeServerCubebox):
        """A common test to badge a team in on a cubebox and check:
        - that the cubebox is playing
        - that the team is associated with the cubebox
        """
        # badge the team in
        uid = team.rfid_uid
        cube_id = cubebox.status.cube_id
        team_name = team.name
        cubebox.rfid.simulate_read(uid)

        # check that the cubebox and cubemaster are up to date with this badge-in
        self.wait_until(lambda: cubebox.is_box_being_played() is True,
                        message="waiting for the box to be played",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: cubebox.is_box_being_played() is True,
                  "Cubebox should be playing")

        if cubebox in self.local_cubeboxes:
            self.test_eq(lambda: cubebox.neopixel.color, CubeNeopixel.HUE_CURRENTLY_PLAYING, "Cubebox should be playing")

        self.test(lambda: cubebox.status.last_valid_rfid_line is not None,
                  "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, uid,
                     "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, cube_id,
                     "Team should be associated with the cubebox")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).start_timestamp is not None,
                  "Team should have a starting timestamp")

    def partial_test_reset_cubebox_with_rfid(self, cubebox:CubeServerCubebox, rfid_uid:str=None):
        """A common test to reset a cubebox with a RFID read and check:
        - that the cubebox is ready to play
        - that the neopixel color is correct
        """
        rfid_uid = rfid_uid or get_random_resetter_uid()
        cubebox.rfid.simulate_read(rfid_uid)
        self.wait_until(lambda: cubebox.status.is_ready_to_play() is True,
                        message="waiting for cubebox to be ready to play",
                        timeout=1)
        self.test(lambda: cubebox.status.is_ready_to_play() is True, "Cubebox should be ready to play")

        if cubebox in self.local_cubeboxes:
            self.test_eq(lambda: cubebox.neopixel.color, CubeNeopixel.HUE_WAITING_FOR_RESET, "Cubebox should be waiting for reset")
            self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
            self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, rfid_uid,
                         "Cubebox should have the correct RFID UID")

    def partial_test_button_press_while_team_playing(self, cubebox:CubeSimBox, team_name:str):
        """A common test to simulate a button press while a team is playing and check:
        - that the cubebox is not playing anymore
        - that the team is not associated with the cubebox anymore
        - that the team has a completed cubebox
        """
        cubebox.simulate_button_long_press()
        self.wait_until(lambda: cubebox.is_box_being_played() is False,
                        message="waiting for the box to stop playing",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: cubebox.is_box_being_played() is False, "Cubebox should not be playing")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line, None, "Cubebox should not have a valid RFID line")
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id is None,
                        message="waiting for the team to be disassociated from the cubebox",
                        timeout=self.COMM_DELAY_SEC)
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, None,
                     "Team should not be associated with the cubebox")
        self.test(lambda: cubebox.cube_id in self.master.teams.get_team_by_name(team_name).completed_cubebox_ids,
                  description="Team should have the cubebox in its completed cubeboxes")

    def full_test_valid_simulation(self):
        self.common_start()
        assert self.cubeboxes[0] in self.local_cubeboxes
        cubebox:CubeServerCubebox = self.cubeboxes[0]
        team_name = "Paris"
        team_custom_name = "Paris Custom"
        cube_id = 1
        rfid_uid = CubeRfidLine.generate_random_rfid_line().uid
        rfid_uid2 = CubeRfidLine.generate_random_rfid_line().uid
        rfid_uid_resetter = CubeRfidLine.get_resetter_uids_list()[0]
        max_time = 3650.0

        if cubebox in self.local_cubeboxes:
            cubebox:CubeServerCubebox
            cubebox.net.log.setLevel(logging.CRITICAL)
        if self.cubemaster_is_local():
            self.master.log.setLevel(logging.CRITICAL)
            self.master.net.log.setLevel(logging.CRITICAL)
        self.frontdesk.log.setLevel(logging.CRITICAL)
        self.frontdesk.net.log.setLevel(logging.CRITICAL)

        team = cgame.CubeTeamStatus(name=team_name, custom_name=team_custom_name, rfid_uid=rfid_uid, max_time_sec=max_time)
        self.partial_test_create_new_team(team)

        self.partial_test_reset_cubebox_with_rfid(cubebox, rfid_uid_resetter)

        self.partial_test_badge_team_in_cubebox(team, cubebox)

        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).completed_cubeboxes, [],
                     "Team should not have completed any cubeboxes")
        self.test_eq(lambda: str(self.master.teams.get_team_by_name(team_name).max_time_sec), str(max_time),
                     "Team should have the correct max time")


        self.wait(0.5, "waiting a bit...")
        self.log.infoplus("Simulating a new RFID read with the same UID")
        cubebox.simulate_rfid_read(rfid_uid)

        self.test(lambda: cubebox.is_box_being_played() is True, "Cubebox should still be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line.uid == rfid_uid, "Cubebox should have retained the same RFID UID")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id == cube_id, "Team should still be associated with the cubebox")

        self.wait(1, "simulating game time...")

        self.partial_test_button_press_while_team_playing(cubebox, team_name)

    def full_test_unregistered_rfid(self):
        cubebox = self.cubeboxes[0]
        self.common_start()
        team_name = "Paris"
        correct_uid = "1234567890"
        incorrect_uid = "1234567891"
        cube_id = 1
        team = cgame.CubeTeamStatus(name=team_name, rfid_uid=correct_uid, max_time_sec=3650)
        self.frontdesk.add_new_team(team)
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name) is not None, message="waiting for the team to be added to the master", timeout=self.COMM_DELAY_SEC)
        cubebox.rfid.simulate_read(incorrect_uid)
        self.wait(self.COMM_DELAY_SEC, "waiting for the rfid msg to be sent to the master")
        self.log.info(f"CUBEBOX.is_box_being_played()={cubebox.is_box_being_played()}")
        self.test(lambda: cubebox.is_box_being_played() is False, "Cubebox should not be playing")

    def full_test_testing_system(self):
        self.log.critical("Testing test()")
        self.test(lambda: 1 == 1, "should pass")
        self.test(lambda: 1 == 2, "should fail")
        self.test(lambda: 2 == 2, "should pass")

        self.log.critical("Testing test_eq()")
        def get_one():
            return 1
        self.test_eq(1, 1, "should pass: 1 should be equal to 1")
        self.test_eq(get_one(), 1, "should pass: get_one() should be equal to 1")
        self.test_eq(lambda: 1, 1, "should pass: lambda: 1 should be equal to 1")
        self.test_eq(1, 2, "should fail: 1 == 2, hurr durr")
        self.test_eq(get_one(), 2, "should fail: get_one() == 2, hurr durr")
        self.test_eq(lambda: 1, 2, "should fail: lambda: 1 == 2, hurr durr")

        self.log.critical("Testing test_neq()")
        self.test_neq(1, 2, "should pass: 1 != 2")
        self.test_neq(get_one(), 2, "should pass: get_one() != 2")
        self.test_neq(lambda: 1, 2, "should pass: lambda: 1 != 2")
        self.test_neq(1, 1, "should fail: 1 != 1, hurr durr")
        self.test_neq(get_one(), 1, "should fail: get_one() != 1, hurr durr")
        self.test_neq(lambda: 1, 1, "should fail: lambda: 1 != 1, hurr durr")

    def full_test_alarm_triggering(self):
        """simulates the following scenario:
        - a team is registered on the frontdesk, with the flag 'use_alarm', and its info is sent to the cubemaster
        - we check that the cubemaster has got the right team info
        - we simulate a RFID read on the cubebox with the team's RFID UID
        - we check that the cubebox is playing
        - we simulate a long press on the cubebox after a few seconds
        - we check that the cubebox is not playing anymore
        - we check that the cubemaster has updated the team's status
        - we check that at some point, the cubemaster has triggered the alarm
        """
        cubebox = self.cubeboxes[0]
        self.log.setLevel(logging.INFO)
        self.common_start()
        team_name = "Paris"
        rfid_uid = CubeRfidLine.generate_random_rfid_line().uid
        cube_id = 1

        max_time_sec = 3650
        team = cgame.CubeTeamStatus(name=team_name, rfid_uid=rfid_uid, max_time_sec=max_time_sec, use_alarm=True)
        self.frontdesk.add_new_team(team)
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name) is not None,
                        message="waiting for the team to be added to the master",
                        timeout=self.COMM_DELAY_SEC)
        self.log.info(f"MASTER.teams.get_team_by_name(team_name)={self.master.teams.get_team_by_name(team_name)}")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).use_alarm, True, "Team should have the alarm flag set")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, None,
                     "Team should not be associated with a cubebox")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).completed_cubebox_ids, [],
                     "Team should not have completed any cubeboxes")
        self.test_eq(lambda: self.master._is_running_alarm, False,
                     "The alarm should not be playing")

        time.sleep(1)
        cubebox.rfid.simulate_read(rfid_uid)
        self.wait_until(lambda: cubebox.is_box_being_played() is True,
                        message="waiting for the box to be played",
                        timeout=self.COMM_DELAY_SEC)
        self.log.info(f"Cubebox status: {cubebox.to_string()}")
        self.test(lambda: cubebox.is_box_being_played() is True, "Cubebox should be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, rfid_uid, "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, cube_id,
                     "Team should be associated with the cubebox")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name)._completed_cubeboxes, [],
                     "Team should not have completed any cubeboxes")
        self.test_eq(lambda: int(self.master.teams.get_team_by_name(team_name).max_time_sec), int(max_time_sec),
                     "Team should have the correct max time")
        self.log.info(f"Master teams status: {self.master.teams.to_string()}")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).start_timestamp is not None,
                  "Team should have a starting timestamp")
        self.wait(2, "waiting a bit...")
        self.log.info("Simulating long press")
        cubebox.button.simulate_long_press()
        self.wait_until(lambda: self.master._is_running_alarm is True,
                        message="waiting for the alarm to be triggered",
                        timeout=self.COMM_DELAY_SEC)
        self.log.info(f"MASTER._is_playing_alarm={self.master._is_running_alarm}")
        self.test(lambda: self.master._is_running_alarm is True, "The alarm should be playing")
        self.wait_until(lambda: cubebox.is_box_being_played() is False,
                        message="waiting for the box to stop playing",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: cubebox.is_box_being_played() is False,
                  "Cubebox should not be playing")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id is None,
                  "Team should not be associated with a cubebox")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).completed_cubebox_ids == [cube_id],
                  f"Team should have completed cubebox {cube_id}")

    def full_test_team_time_up(self):
        """simulates the following scenario:
        - a team is registered on the frontdesk. The team has a max time of 1 second.
        - we check that the cubemaster has got the right team info
        - we simulate a RFID read on the cubebox with the team's RFID UID
        - we check that the cubebox is playing (wait_until)
        - we wait for the team's time to be up (wait_until)
        - we check that the cubebox is not playing anymore (wait_until)
        - we check that the cubemaster has removed the team from the list of active teams (wait_until)
        - we check that the frontdesk has removed the team from the list of active teams (wait_until)
        """
        cube_id = random.randint(1, self.nb_cubeboxes)
        cubebox = self.cubeboxes[cube_id - 1]
        self.log.setLevel(logging.INFO)
        self.common_start()
        team_name = "Paris"
        rfid_uid = CubeRfidLine.generate_random_rfid_line().uid
        max_time_sec = 1

        team = cgame.CubeTeamStatus(name=team_name, rfid_uid=rfid_uid, max_time_sec=max_time_sec)

        self.partial_test_create_new_team(team)

        self.partial_test_badge_team_in_cubebox(team, cubebox)

        # wait for the team's time to be up
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name).is_time_up(),
                        message="waiting for the team's time to be up",
                        timeout=max_time_sec + 1)

        # check that the cubebox is up to date
        self.wait_until(lambda: cubebox.is_box_being_played() is False,
                        message="waiting for the box to stop playing",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: cubebox.is_box_being_played() is False, "Cubebox should not be playing")
        self.test_eq(lambda: cubebox.status.is_waiting_for_reset(), True, "Cubebox should be waiting for reset")


        # check that the frontdesk is up to date
        self.wait_until(lambda: self.frontdesk.teams.get_team_by_name(team_name) is None,
                        message="waiting for the team to be removed from the frontdesk",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: self.frontdesk.teams.get_team_by_name(team_name) is None,
                  "Team should not be in the frontdesk's current teams")

        # check that the cubemaster is up to date
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name) is None,
                        message="waiting for the team to be removed from the master",
                        timeout=self.COMM_DELAY_SEC)
        self.test(lambda: self.master.teams.get_team_by_name(team_name) is None,
                    "Team should not be in the master's active teams")
        self.test(lambda: self.master.database.find_team_by_creation_timestamp(team.creation_timestamp) is not None,
                   "Team should be in the master database")

        time.sleep(2)


if __name__ == "__main__":
    cube_tester = CubeTester(nb_cubeboxes=1)
    try:
        # cube_tester.test_testing_system()
        # exit(0)
        cube_tester.set_every_node_to_local()
        # cube_tester.set_cubemaster_to_remote()
        cube_tester.full_test_valid_simulation()
        # cube_tester.test_alarm_triggering()
        # cube_tester.full_test_unregistered_rfid()
        # cube_tester.test_testing_system()
        # cube_tester.full_test_team_time_up()
    except Exception as e:
        cube_tester.log.error(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        cube_tester.stop_simulation()
        cube_tester.log.setLevel(logging.DEBUG)
        cube_tester.display_results()
        exit(0)
