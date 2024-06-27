import inspect
import logging
import re
import threading
import traceback
from typing import List, Callable

from thecubeivazio import cube_logger
from thecubeivazio import cubeserver_cubebox, cubeserver_frontdesk, cubeserver_cubemaster
from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_messages as cm
from thecubeivazio import cube_utils
from thecubeivazio import cube_game
import time

from thecubeivazio.cube_common_defines import *
from thecubeivazio.cube_rfid import CubeRfidLine

COMM_DELAY_SEC = 3
CUBE_ID = 1
LOGGER = cube_logger.CubeLogger("Simulations")
CUBEBOX = cubeserver_cubebox.CubeServerCubebox(node_name=cubeid.cubebox_index_to_node_name(CUBE_ID))
FRONTDESK = cubeserver_frontdesk.CubeServerFrontdesk()
MASTER = cubeserver_master.CubeServerMaster()
CUBEBOX_THREAD = threading.Thread(target=CUBEBOX.run)
FRONTDESK_THREAD = threading.Thread(target=FRONTDESK.run)
MASTER_THREAD = threading.Thread(target=MASTER.run)

# disable RFID listeners, we will simulate the RFID reads
CUBEBOX.rfid._is_enabled = False
FRONTDESK.rfid._is_enabled = False
MASTER.rfid._is_enabled = False

class TestResults:
    RESULT_PASS = "PASS"
    RESULT_FAIL = "FAIL"

    def __init__(self):
        self.statements = []
        self.results = []

    def add(self, statement, result):
        self.statements.append(statement)
        self.results.append(result)

    def display(self):
        nb_tests = len(self.statements)
        nb_pass = self.results.count(self.RESULT_PASS)
        nb_fail = self.results.count(self.RESULT_FAIL)
        LOGGER.info("TestResults:")
        for i, statement in enumerate(self.statements):
            if self.results[i] == TestResults.RESULT_PASS:
                # LOGGER.info(f"PASS : {statement}: {self.results[i]}")
                LOGGER.debug(f"PASS : {statement}")
            else:
                # LOGGER.warning(f"FAIL : {statement}: {self.results[i]}")
                LOGGER.warning(f"FAIL : {statement}")
        LOGGER.info(f"Results: {nb_pass}/{nb_tests} passed, {nb_fail}/{nb_tests} failed")


RESULTS = TestResults()


def test(statement:Callable, description: str = None, dont_record=False) -> bool:
    global RESULTS
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
            LOGGER.error(f"Exception while testing {statement_str}: {e}")
            traceback.print_exc()
            result = f"FAIL : {e}"
    finally:
        if not dont_record:
            RESULTS.add(statement_str, result)
            if log_in_real_time:
                if result == TestResults.RESULT_FAIL:
                    LOGGER.critical(f"FAIL : {statement_str} : {description}")
                else:
                    LOGGER.debug(f"PASS : {statement_str} : {description}")
        return result == TestResults.RESULT_PASS

def test_neq(a, b, description: str = None) -> bool:
    if callable(a):
        statement_str = inspect.getsource(a).strip()
    else:
        statement_str = f"{a} == {b}"

    a_val = a() if callable(a) else a
    b_val = b() if callable(b) else b
    a_str = f"{a_val}"
    b_str = f"{b_val}"
    # statement_str = f"{a_str} == {b_str}"

    # LOGGER.critical(f"a_str='{a_str}'\nb_str='{b_str}'\nstatement_str='{statement_str}'")
    if a_val == b_val:
        LOGGER.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
        RESULTS.add(statement_str, RESULTS.RESULT_FAIL)
    else:
        LOGGER.debug(f"PASS : {statement_str} : {description}")
        RESULTS.add(statement_str, RESULTS.RESULT_PASS)

def test_eq(a, b, description: str = None) -> bool:
    if callable(a):
        statement_str = inspect.getsource(a).strip()
    else:
        statement_str = f"{a} == {b}"

    a_val = a() if callable(a) else a
    b_val = b() if callable(b) else b
    a_str = f"{a_val}"
    b_str = f"{b_val}"
    # statement_str = f"{a_str} == {b_str}"

    # LOGGER.critical(f"a_str='{a_str}'\nb_str='{b_str}'\nstatement_str='{statement_str}'")
    if a_val != b_val:
        LOGGER.critical(f"FAIL : {statement_str} : {description} : {a_str} should be {b_val}, is {a_val}")
        RESULTS.add(statement_str, RESULTS.RESULT_FAIL)
    else:
        LOGGER.debug(f"PASS : {statement_str} : {description}")
        RESULTS.add(statement_str, RESULTS.RESULT_PASS)

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

def wait(seconds, message: str = None):
    if message is not None:
        LOGGER.info(f"sleeping for {seconds}s : {message}")
    else:
        LOGGER.info(f"sleeping for {seconds}s")
    time.sleep(seconds)


def wait_until(condition:Callable, timeout=5, message: str = None):
    start_time = time.time()
    if message is None:
        message = inspect.getsource(condition).strip()
    LOGGER.info(f"sleeping for {timeout}s max : {message}")
    try:
        while time.time() - start_time < timeout:
            if condition():
                return
            time.sleep(0.1)
        LOGGER.warning(f"Timeout of {timeout}s reached while waiting for '{message}'")
    except Exception as e:
        LOGGER.error(f"An error occurred while waiting for '{condition}': {e}")
        traceback.print_exc()


def common_start():
    CUBEBOX_THREAD.start()
    FRONTDESK_THREAD.start()
    MASTER_THREAD.start()
    CUBEBOX.log.setLevel(logging.INFO)
    CUBEBOX.net.log.setLevel(logging.INFO)
    FRONTDESK.log.setLevel(logging.INFO)
    FRONTDESK.net.log.setLevel(logging.INFO)
    MASTER.log.setLevel(logging.INFO)
    MASTER.net.log.setLevel(logging.INFO)


def valid_simulation():
    global CUBEBOX, FRONTDESK, MASTER
    common_start()
    team_name = "Paris"
    team_custom_name = "Paris Custom"
    cube_id = 1
    rfid_uid = CubeRfidLine.generate_random_rfid_line().uid
    rfid_uid2 = CubeRfidLine.generate_random_rfid_line().uid
    rfid_uid_resetter = "11111111"
    max_time:Seconds = 3650.0

    # mute some logs

    # CUBEBOX.log.setLevel(logging.CRITICAL)
    CUBEBOX.net.log.setLevel(logging.CRITICAL)
    # MASTER.log.setLevel(logging.CRITICAL)
    # MASTER.net.log.setLevel(logging.CRITICAL)
    FRONTDESK.log.setLevel(logging.CRITICAL)
    FRONTDESK.net.log.setLevel(logging.CRITICAL)
    # LOGGER.setLevel(logging.CRITICAL)

    # simulate the frontdesk creating a new team
    team = cube_game.CubeTeamStatus(name=team_name, custom_name=team_custom_name, rfid_uid=rfid_uid, max_time_sec=max_time)
    LOGGER.infoplus("Frontdesk Adding a new team")
    FRONTDESK.add_new_team(team)
    # wait(COMM_DELAY_SEC, "waiting for the team to be added to the master")
    wait_until(lambda: MASTER.teams.get_team_by_name(team_name) is not None,
               message="waiting for the team to be added to the master",
               timeout=COMM_DELAY_SEC)
    LOGGER.infoplus("Simulating RFID reset on Cubebox")
    CUBEBOX.rfid.simulate_read(rfid_uid_resetter)
    wait_until(lambda: CUBEBOX.status.is_ready_to_play() is True,
               message="waiting for cubebox to be ready to play",
               timeout=1)
    test(lambda: CUBEBOX.status.is_ready_to_play(), "Cubebox should be ready to play")
    LOGGER.infoplus("Simulating RFID read on Cubebox")
    CUBEBOX.rfid.simulate_read(team.rfid_uid)
    LOGGER.infoplus(f"CUBEBOX.last_valid_rfid_line={CUBEBOX.status.last_valid_rfid_line}")
    wait_until(lambda : CUBEBOX.status.last_valid_rfid_line,
               message="waiting for cubebox to have a valid rfid line",
               timeout=1)
    # wait(COMM_DELAY_SEC, "waiting for the rfid msg to be sent to the master")
    wait_until(lambda: CUBEBOX.is_box_being_played() is True,
               message="waiting for the box to be played",
               timeout=COMM_DELAY_SEC)
    LOGGER.info(f"Cubebox status: {CUBEBOX.to_string()}")
    test(lambda: CUBEBOX.is_box_being_played(), "Cubebox should be playing")
    test(lambda: CUBEBOX.status.last_valid_rfid_line is not None, "Cubebox should have a valid RFID line")
    test_eq(lambda: CUBEBOX.status.last_valid_rfid_line.uid, rfid_uid, "Cubebox should have the correct RFID UID")
    test_eq(lambda: MASTER.teams.get_team_by_name(team_name).current_cubebox_id, cube_id,
         "Team should be associated with the cubebox")
    test_eq(lambda: MASTER.teams.get_team_by_name(team_name)._completed_cubeboxes, [],
         "Team should not have completed any cubeboxes")
    test_eq(lambda: str(MASTER.teams.get_team_by_name(team_name).max_time_sec), str(max_time),
         "Team should have the correct max time")
    LOGGER.info(f"Master teams status: {MASTER.teams.to_string()}")
    test(lambda: MASTER.teams.get_team_by_name(team_name).start_timestamp is not None,
         "Team should have a starting timestamp")
    wait(0.5, "waiting a bit...")
    LOGGER.infoplus("Simulating a new RFID read with the same UID")
    CUBEBOX.rfid.simulate_read(rfid_uid)

    test(lambda: CUBEBOX.is_box_being_played() is True, "Cubebox should still be playing")
    test(lambda: CUBEBOX.status.last_valid_rfid_line.uid == rfid_uid, "Cubebox should have retained the same RFID UID")
    test(lambda: MASTER.teams.get_team_by_name(team_name).current_cubebox_id == cube_id,
         "Team should still be associated with the cubebox")

    wait(1, "simulating game time...")

    LOGGER.infoplus("Simulating long press")
    CUBEBOX.button.simulate_long_press()

    wait_until(lambda: MASTER.teams.get_team_by_name(team_name).current_cubebox_id \
                       and CUBEBOX.is_box_being_played() is False,
               message="waiting for cubemaster and cubebox to update their status",
               timeout=COMM_DELAY_SEC)
    LOGGER.info(f"Cubebox status: {CUBEBOX.to_string()}")
    LOGGER.info(f"Master teams status: {MASTER.teams.to_string()}")
    test(lambda: CUBEBOX.is_box_being_played() is False, "Cubebox should not be playing")
    test(lambda: CUBEBOX.status.is_waiting_for_reset() is True, "Cubebox should be waiting for reset")
    team_from_cubemaster = MASTER.teams.get_team_by_name(team_name)
    test(lambda: team_from_cubemaster is not None, "Team should still be in the master")
    test(lambda: team_from_cubemaster.current_cubebox_id is None, "Team should not be associated with a cubebox")
    test(lambda: team_from_cubemaster.completed_cubebox_ids == [cube_id], "Team should have completed cubebox 1")


def unregistered_rfid():
    common_start()
    team_name = "Paris"
    rfid_uid = "1234567890"
    cube_id = 1
    # simulate the frontdesk creating a new team
    team = cube_game.CubeTeamStatus(name=team_name, rfid_uid=rfid_uid, max_time_sec=3650)
    FRONTDESK.add_new_team(team)
    # wait(COMM_DELAY_SEC, "waiting for the team to be added to the master")
    wait_until(lambda: MASTER.teams.get_team_by_name(team_name) is not None,
               message="waiting for the team to be added to the master",
               timeout=STATUS_REPLY_TIMEOUT)

    CUBEBOX.rfid.simulate_read("1234567891")
    wait(COMM_DELAY_SEC, "waiting for the rfid msg to be sent to the master")
    LOGGER.info(f"CUBEBOX.is_box_being_played()={CUBEBOX.is_box_being_played()}")
    test(lambda: CUBEBOX.is_box_being_played() is False, "Cubebox should not be playing")


def test_testing_system():
    LOGGER.critical("Testing test()")
    test(lambda: 1 == 1, "should pass")
    test(lambda: 1 == 2, "should fail")
    test(lambda: 2 == 2, "should pass")

    LOGGER.critical("Testing test_eq()")
    def get_one():
        return 1
    test_eq(1, 1, "should pass: 1 should be equal to 1")
    test_eq(get_one(), 1, "should pass: get_one() should be equal to 1")
    test_eq(lambda: 1, 1, "should pass: lambda: 1 should be equal to 1")
    test_eq(1, 2, "should fail: 1 == 2, hurr durr")
    test_eq(get_one(), 2, "should fail: get_one() == 2, hurr durr")
    test_eq(lambda: 1, 2, "should fail: lambda: 1 == 2, hurr durr")

    LOGGER.critical("Testing test_neq()")
    test_neq(1, 2, "should pass: 1 != 2")
    test_neq(get_one(), 2, "should pass: get_one() != 2")
    test_neq(lambda: 1, 2, "should pass: lambda: 1 != 2")
    test_neq(1, 1, "should fail: 1 != 1, hurr durr")
    test_neq(get_one(), 1, "should fail: get_one() != 1, hurr durr")
    test_neq(lambda: 1, 1, "should fail: lambda: 1 != 1, hurr durr")

def stop_simulation():
    try:
        LOGGER.info("Stopping the servers")
        CUBEBOX.stop()
        FRONTDESK.stop()
        MASTER.stop()
        CUBEBOX_THREAD.join(timeout=0.1)
        FRONTDESK_THREAD.join(timeout=0.1)
        MASTER_THREAD.join(timeout=0.1)
    except Exception as e:
        LOGGER.error(f"An error occurred while stopping the servers: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # test_testing_system()
        # exit(0)
        valid_simulation()
        # time.sleep(5)
        # unregistered_rfid()
        # test_testing_system()
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        stop_simulation()
        LOGGER.setLevel(logging.DEBUG)
        RESULTS.display()
        exit(0)
