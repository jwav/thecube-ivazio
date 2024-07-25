import logging
import random
import re
import threading
import time
from typing import Callable

from thecubeivazio import cube_game as cgame
from thecubeivazio import cube_logger
from thecubeivazio.cube_neopixel import CubeNeopixel
from thecubeivazio.cubeserver_cubebox import CubeServerCubebox
from thecubeivazio.cubeserver_frontdesk import CubeServerFrontdesk
from thecubeivazio.cubeserver_cubemaster import CubeServerMaster
from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_rfid import CubeRfidLine
from thecubeivazio import cube_database as cubedb


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


class CubeTester:
    COMM_DELAY_SEC = 3

    def __init__(self, name="CubeTester", nb_cubeboxes=1):
        self.cube_id = 1
        self.name = name
        self.logger = cube_logger.CubeLogger(name)
        self._cubeboxes = [CubeServerCubebox(i+1) for i in range(nb_cubeboxes)]
        self.frontdesk = CubeServerFrontdesk()
        self.master = CubeServerMaster()
        self.cubebox_threads = [threading.Thread(target=cubebox.run, daemon=True) for cubebox in self._cubeboxes]
        self.frontdesk_thread = threading.Thread(target=self.frontdesk.run, daemon=True)
        self.master_thread = threading.Thread(target=self.master.run, daemon=True)
        self.results = TestResults()
        # if this flag is False, the cubebox instances will be locally defined instances of CubeServerCubebox
        # if this flag is True, we expect that actual cubeboxes are running on the network.
        # The local instances used for testing will be updated with status replies from the cubeboxes,
        # triggered by requests from the (local) frontdesk.
        # see update_cubeboxes_statuses in this class for more details.
        self.test_remotely = False

    @property
    def cubeboxes(self):
        if not self.test_remotely:
            return self._cubeboxes
        else:
            return self.frontdesk.cubeboxes

    @property
    def nb_cubeboxes(self):
        return len(self._cubeboxes)

    @property
    def cubeboxes_ids(self) -> list[CubeId]:
        return [cubebox.status.cube_id for cubebox in self._cubeboxes]

    def update_cubeboxes_statuses(self) -> bool:
        if not self.test_remotely:
            return True
        ret = True
        for cube_id in self.cubeboxes_ids:
            if not self.frontdesk.request_cubebox_status(cube_id):
                self.logger.error(f"Error requesting status for cubebox {cube_id}")
                ret = False
        return ret

    def common_start(self):
        """Common setup for the tests:
        - start the servers
        - set the log levels to INFO
        - disable the RFID listeners
        - use custom databases
        """
        for cubebox_thread in self.cubebox_threads:
            cubebox_thread.start()
        self.frontdesk_thread.start()
        self.master_thread.start()
        for cubebox in self.cubeboxes:
            cubebox.log.setLevel(logging.INFO)
            cubebox.net.log.setLevel(logging.INFO)
        self.frontdesk.log.setLevel(logging.INFO)
        self.frontdesk.net.log.setLevel(logging.INFO)
        self.master.log.setLevel(logging.INFO)
        self.master.net.log.setLevel(logging.INFO)
        # disable RFID listeners, we will simulate the RFID reads
        for cubebox in self.cubeboxes:
            cubebox.rfid.disable()
        self.master.rfid.disable()
        self.frontdesk.rfid.disable()
        # use custom databases just for the simulation
        master_db_filename = os.path.join(SAVES_DIR, "master_test.db")
        frontdesk_db_filename = os.path.join(SAVES_DIR, "frontdesk_test.db")
        self.master.database = cubedb.CubeDatabase(master_db_filename)
        self.master.database.clear_database()
        self.frontdesk.database = cubedb.CubeDatabase(frontdesk_db_filename)
        self.frontdesk.database.clear_database()

    def stop_simulation(self):
        try:
            self.logger.info("Stopping the servers")
            for cubebox in self.cubeboxes:
                cubebox.stop()
            self.frontdesk.stop()
            self.master.stop()
            for cubebox_thread in self.cubebox_threads:
                cubebox_thread.join(timeout=0.1)
            self.frontdesk_thread.join(timeout=0.1)
            self.master_thread.join(timeout=0.1)
        except Exception as e:
            self.logger.error(f"An error occurred while stopping the servers: {e}")
            traceback.print_exc()

    def display_results(self):
        nb_tests = len(self.results.statements)
        nb_pass = self.results.results.count(TestResults.RESULT_PASS)
        nb_fail = self.results.results.count(TestResults.RESULT_FAIL)
        self.logger.info("\n--------------------\nTestResults:\n--------------------\n")
        for i, statement in enumerate(self.results.statements):
            if self.results.results[i] == TestResults.RESULT_PASS:
                # LOGGER.info(f"PASS : {statement}: {self.results[i]}")
                self.logger.success(f"PASS : {statement}")
            else:
                # LOGGER.warning(f"FAIL : {statement}: {self.results[i]}")
                self.logger.critical(f"FAIL : {statement}")
        # display the failed tests
        if nb_fail > 0:
            self.logger.critical("\n--------------------\nFailed tests:\n--------------------\n")
        for i, statement in enumerate(self.results.statements):
            if self.results.results[i] == TestResults.RESULT_FAIL:
                self.logger.critical(f"FAIL : {statement}")
        self.logger.info(f"Results: {nb_pass}/{nb_tests} passed, {nb_fail}/{nb_tests} failed")

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
                self.logger.error(f"Exception while testing {statement_str}: {e}")
                traceback.print_exc()
                result = f"FAIL : {e}"
        finally:
            if not dont_record:
                self.results.add(statement_str, result)
                if log_in_real_time:
                    if result == TestResults.RESULT_FAIL:
                        self.logger.critical(f"FAIL : {statement_str} : {description}")
                    else:
                        self.logger.debug(f"PASS : {statement_str} : {description}")
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
            self.logger.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
            self.results.add(statement_str, self.results.RESULT_FAIL)
            return True
        else:
            self.logger.debug(f"PASS : {statement_str} : {description}")
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
            self.logger.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
            self.results.add(statement_str, self.results.RESULT_FAIL)
            return True
        else:
            self.logger.debug(f"PASS : {statement_str} : {description}")
            self.results.add(statement_str, self.results.RESULT_PASS)
            return False

    def wait(self, seconds, message: str = None):
        if message is not None:
            self.logger.info(f"sleeping for {seconds}s : {message}")
        else:
            self.logger.info(f"sleeping for {seconds}s")
        time.sleep(seconds)

    def wait_until(self, condition: Callable, timeout=5, message: str = None):
        start_time = time.time()
        if message is None:
            message = inspect.getsource(condition).strip()
        self.logger.info(f"sleeping for {timeout}s max : {message}")
        try:
            while time.time() - start_time < timeout:
                if condition():
                    return
                time.sleep(0.1)
            self.logger.warning(f"Timeout of {timeout}s reached while waiting for '{message}'")
        except Exception as e:
            self.logger.error(f"An error occurred while waiting for '{condition}': {e}")
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
        self.test(lambda: cubebox.is_box_being_played() is True, "Cubebox should be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, uid, "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: cubebox.neopixel.color, CubeNeopixel.COLOR_CURRENTLY_PLAYING, "Cubebox should be playing")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, cube_id,
                     "Team should be associated with the cubebox")

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
        self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, rfid_uid, "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: cubebox.neopixel.color, CubeNeopixel.COLOR_WAITING_FOR_RESET, "Cubebox should be waiting for reset")


    def full_test_valid_simulation(self):
        self.common_start()
        cubebox = self.cubeboxes[0]
        team_name = "Paris"
        team_custom_name = "Paris Custom"
        cube_id = 1
        rfid_uid = CubeRfidLine.generate_random_rfid_line().uid
        rfid_uid2 = CubeRfidLine.generate_random_rfid_line().uid
        rfid_uid_resetter = CubeRfidLine.get_resetter_uids_list()[0]
        max_time = 3650.0

        cubebox.net.log.setLevel(logging.CRITICAL)
        self.master.log.setLevel(logging.CRITICAL)
        self.master.net.log.setLevel(logging.CRITICAL)
        self.frontdesk.log.setLevel(logging.CRITICAL)
        self.frontdesk.net.log.setLevel(logging.CRITICAL)

        team = cgame.CubeTeamStatus(name=team_name, custom_name=team_custom_name, rfid_uid=rfid_uid, max_time_sec=max_time)
        self.logger.infoplus("Frontdesk Adding a new team")
        self.frontdesk.add_new_team(team)
        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name) is not None, message="waiting for the team to be added to the master", timeout=self.COMM_DELAY_SEC)
        self.logger.infoplus("Simulating RFID reset on Cubebox")
        cubebox.rfid.simulate_read(rfid_uid_resetter)
        self.wait_until(lambda: cubebox.status.is_ready_to_play() is True, message="waiting for cubebox to be ready to play", timeout=1)
        self.test(lambda: cubebox.status.is_ready_to_play(), "Cubebox should be ready to play")
        self.logger.infoplus("Simulating RFID read on Cubebox")
        cubebox.rfid.simulate_read(team.rfid_uid)
        self.logger.infoplus(f"CUBEBOX.last_valid_rfid_line={cubebox.status.last_valid_rfid_line}")
        self.wait_until(lambda: cubebox.status.last_valid_rfid_line, message="waiting for cubebox to have a valid rfid line", timeout=1)
        self.wait_until(lambda: cubebox.is_box_being_played() is True, message="waiting for the box to be played", timeout=self.COMM_DELAY_SEC)
        self.logger.info(f"Cubebox status: {cubebox.to_string()}")
        self.test(lambda: cubebox.is_box_being_played(), "Cubebox should be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, rfid_uid, "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, cube_id, "Team should be associated with the cubebox")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).completed_cubeboxes, [], "Team should not have completed any cubeboxes")
        self.test_eq(lambda: str(self.master.teams.get_team_by_name(team_name).max_time_sec), str(max_time), "Team should have the correct max time")
        self.logger.info(f"Master teams status: {self.master.teams.to_string()}")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).start_timestamp is not None, "Team should have a starting timestamp")
        self.wait(0.5, "waiting a bit...")
        self.logger.infoplus("Simulating a new RFID read with the same UID")
        cubebox.rfid.simulate_read(rfid_uid)

        self.test(lambda: cubebox.is_box_being_played() is True, "Cubebox should still be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line.uid == rfid_uid, "Cubebox should have retained the same RFID UID")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id == cube_id, "Team should still be associated with the cubebox")

        self.wait(1, "simulating game time...")

        self.logger.infoplus("Simulating long press")
        cubebox.button.simulate_long_press()

        self.wait_until(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id is None and cubebox.is_box_being_played() is False, message="waiting for cubemaster and cubebox to update their status", timeout=self.COMM_DELAY_SEC)
        self.logger.info(f"Cubebox status: {cubebox.to_string()}")
        self.logger.info(f"Master teams status: {self.master.teams.to_string()}")
        self.test(lambda: cubebox.is_box_being_played() is False, "Cubebox should not be playing")
        self.test(lambda: cubebox.status.is_waiting_for_reset() is True, "Cubebox should be waiting for reset")
        team_from_cubemaster = self.master.teams.get_team_by_name(team_name)
        self.test(lambda: team_from_cubemaster is not None, "Team should still be in the master")
        self.test(lambda: team_from_cubemaster.current_cubebox_id is None, "Team should not be associated with a cubebox")
        self.test(lambda: team_from_cubemaster.completed_cubebox_ids == [cube_id], "Team should have completed cubebox 1")

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
        self.logger.info(f"CUBEBOX.is_box_being_played()={cubebox.is_box_being_played()}")
        self.test(lambda: cubebox.is_box_being_played() is False, "Cubebox should not be playing")

    def full_test_testing_system(self):
        self.logger.critical("Testing test()")
        self.test(lambda: 1 == 1, "should pass")
        self.test(lambda: 1 == 2, "should fail")
        self.test(lambda: 2 == 2, "should pass")

        self.logger.critical("Testing test_eq()")
        def get_one():
            return 1
        self.test_eq(1, 1, "should pass: 1 should be equal to 1")
        self.test_eq(get_one(), 1, "should pass: get_one() should be equal to 1")
        self.test_eq(lambda: 1, 1, "should pass: lambda: 1 should be equal to 1")
        self.test_eq(1, 2, "should fail: 1 == 2, hurr durr")
        self.test_eq(get_one(), 2, "should fail: get_one() == 2, hurr durr")
        self.test_eq(lambda: 1, 2, "should fail: lambda: 1 == 2, hurr durr")

        self.logger.critical("Testing test_neq()")
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
        self.logger.setLevel(logging.INFO)
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
        self.logger.info(f"MASTER.teams.get_team_by_name(team_name)={self.master.teams.get_team_by_name(team_name)}")
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
        self.logger.info(f"Cubebox status: {cubebox.to_string()}")
        self.test(lambda: cubebox.is_box_being_played() is True, "Cubebox should be playing")
        self.test(lambda: cubebox.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
        self.test_eq(lambda: cubebox.status.last_valid_rfid_line.uid, rfid_uid, "Cubebox should have the correct RFID UID")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name).current_cubebox_id, cube_id,
                     "Team should be associated with the cubebox")
        self.test_eq(lambda: self.master.teams.get_team_by_name(team_name)._completed_cubeboxes, [],
                     "Team should not have completed any cubeboxes")
        self.test_eq(lambda: int(self.master.teams.get_team_by_name(team_name).max_time_sec), int(max_time_sec),
                     "Team should have the correct max time")
        self.logger.info(f"Master teams status: {self.master.teams.to_string()}")
        self.test(lambda: self.master.teams.get_team_by_name(team_name).start_timestamp is not None,
                  "Team should have a starting timestamp")
        self.wait(2, "waiting a bit...")
        self.logger.info("Simulating long press")
        cubebox.button.simulate_long_press()
        self.wait_until(lambda: self.master._is_running_alarm is True,
                        message="waiting for the alarm to be triggered",
                        timeout=self.COMM_DELAY_SEC)
        self.logger.info(f"MASTER._is_playing_alarm={self.master._is_running_alarm}")
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
        self.logger.setLevel(logging.INFO)
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
        # cube_tester.valid_simulation()
        # cube_tester.test_alarm_triggering()
        # cube_tester.unregistered_rfid()
        # cube_tester.test_testing_system()
        cube_tester.full_test_team_time_up()
    except Exception as e:
        cube_tester.logger.error(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        cube_tester.stop_simulation()
        cube_tester.logger.setLevel(logging.DEBUG)
        cube_tester.display_results()
        exit(0)
