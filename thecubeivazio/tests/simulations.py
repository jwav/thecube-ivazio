import inspect
import logging
import threading
import traceback
from typing import List

from thecubeivazio import cube_logger
from thecubeivazio import cubeserver_cubebox, cubeserver_frontdesk, cubeserver_master
from thecubeivazio import cube_identification as cubeid
from thecubeivazio import cube_messages as cm
from thecubeivazio import cube_utils
from thecubeivazio import cube_game
import time

from thecubeivazio.cube_common_defines import *

COMM_DELAY_SEC = 3
CUBE_ID = 1
LOGGER = cube_logger.make_logger("Simulations")
CUBEBOX = cubeserver_cubebox.CubeServerCubebox(node_name=cubeid.cubebox_index_to_node_name(CUBE_ID))
FRONTDESK = cubeserver_frontdesk.CubeServerFrontdesk()
MASTER = cubeserver_master.CubeServerMaster()
CUBEBOX_THREAD = threading.Thread(target=CUBEBOX.run)
FRONTDESK_THREAD = threading.Thread(target=FRONTDESK.run)
MASTER_THREAD = threading.Thread(target=MASTER.run)


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
        LOGGER.info("TestResults:")
        for i, statement in enumerate(self.statements):
            if self.results[i] == TestResults.RESULT_PASS:
                # LOGGER.info(f"PASS : {statement}: {self.results[i]}")
                LOGGER.debug(f"PASS : {statement}")
            else:
                # LOGGER.warning(f"FAIL : {statement}: {self.results[i]}")
                LOGGER.warning(f"FAIL : {statement}")


RESULTS = TestResults()


def test(statement, description: str = None):
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
        LOGGER.error(f"Exception while testing {statement_str}: {e}")
        traceback.print_exc()
        result = f"FAIL : {e}"
    finally:
        RESULTS.add(statement_str, result)
        if log_in_real_time:
            if result == TestResults.RESULT_FAIL:
                LOGGER.critical(f"FAIL : {statement_str}")
            else:
                LOGGER.debug(f"PASS : {statement_str}")


def wait(seconds, message: str = None):
    if message is not None:
        LOGGER.info(f"sleeping for {seconds}s : {message}")
    else:
        LOGGER.info(f"sleeping for {seconds}s")
    time.sleep(seconds)


def wait_until(condition, timeout=5, message: str = None):
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
    cube_id = 1
    rfid_uid = "1234567890"
    rfid_uid2 = "1234567891"
    max_time:Seconds = 3650.0

    # mute some logs

    # CUBEBOX.log.setLevel(logging.CRITICAL)
    CUBEBOX.net.log.setLevel(logging.CRITICAL)
    # MASTER.log.setLevel(logging.CRITICAL)
    MASTER.net.log.setLevel(logging.CRITICAL)
    FRONTDESK.log.setLevel(logging.CRITICAL)
    FRONTDESK.net.log.setLevel(logging.CRITICAL)
    # LOGGER.setLevel(logging.CRITICAL)

    # simulate the frontdesk creating a new team
    team = cube_game.CubeTeamStatus(name=team_name, rfid_uid=rfid_uid, max_time_sec=max_time)
    LOGGER.critical("Frontdesk Adding a new team")
    FRONTDESK.add_new_team(team)
    # wait(COMM_DELAY_SEC, "waiting for the team to be added to the master")
    wait_until(lambda: MASTER.teams.find_team_by_name(team_name) is not None,
               message="waiting for the team to be added to the master",
               timeout=COMM_DELAY_SEC)
    LOGGER.critical("Simulating RFID read on Cubebox")
    CUBEBOX.rfid.simulate_read(team.rfid_uid)
    # wait(COMM_DELAY_SEC, "waiting for the rfid msg to be sent to the master")
    wait_until(lambda: CUBEBOX.is_box_being_played is True,
               message="waiting for the box to be played",
               timeout=COMM_DELAY_SEC)
    LOGGER.info(f"Cubebox status: {CUBEBOX.to_string()}")
    test(lambda: CUBEBOX.is_box_being_played, "Cubebox should be playing")
    test(lambda: CUBEBOX.last_rfid_line.uid == rfid_uid, "Cubebox should have the correct RFID UID")
    test(lambda: MASTER.teams.find_team_by_name(team_name).current_cubebox_id == cube_id,
         "Team should be associated with the cubebox")
    test(lambda: MASTER.teams.find_team_by_name(team_name).completed_cubeboxes == [],
         "Team should not have completed any cubeboxes")
    test(lambda: str(MASTER.teams.find_team_by_name(team_name).max_time_sec) == str(max_time),
         "Team should have the correct max time")
    LOGGER.info(f"Master teams status: {MASTER.teams.to_string()}")
    test(lambda: MASTER.teams.find_team_by_name(team_name).starting_timestamp is not None,
         "Team should have a starting timestamp")
    wait(0.5, "waiting a bit...")
    LOGGER.critical("Simulating a new RFID read with the same UID")
    CUBEBOX.rfid.simulate_read(rfid_uid)

    test(lambda: CUBEBOX.is_box_being_played is True, "Cubebox should still be playing")
    test(lambda: CUBEBOX.last_rfid_line.uid == rfid_uid, "Cubebox should have retained the same RFID UID")
    test(lambda: MASTER.teams.find_team_by_name(team_name).current_cubebox_id == cube_id,
         "Team should still be associated with the cubebox")

    wait(1, "simulating game time...")

    LOGGER.critical("Simulating long press")
    CUBEBOX.button.simulate_long_press()

    wait_until(lambda: MASTER.teams.find_team_by_name(team_name).current_cubebox_id \
                       and CUBEBOX.is_box_being_played is False,
               message="waiting for cubemaster and cubebox to update their status",
               timeout=COMM_DELAY_SEC)
    LOGGER.info(f"Cubebox status: {CUBEBOX.to_string()}")
    LOGGER.info(f"Master teams status: {MASTER.teams.to_string()}")
    test(lambda: CUBEBOX.is_box_being_played is False, "Cubebox should not be playing")
    test(lambda: CUBEBOX.last_rfid_line is None, "Cubebox should not have an RFID UID")
    team_from_cubemaster = MASTER.teams.find_team_by_name(team_name)
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
    wait_until(lambda: MASTER.teams.find_team_by_name(team_name) is not None,
               message="waiting for the team to be added to the master",
               timeout=5)

    CUBEBOX.rfid.simulate_read("1234567891")
    wait(COMM_DELAY_SEC, "waiting for the rfid msg to be sent to the master")
    LOGGER.info(f"CUBEBOX.is_box_being_played={CUBEBOX.is_box_being_played}")
    test(lambda: CUBEBOX.is_box_being_played is False, "Cubebox should not be playing")


def test_testing_system():
    test(lambda: 1 == 1, "1 should be equal to 1")
    test(lambda: 1 == 2, "1 should not be equal to 2")
    test(lambda: 2 == 2, "2 should be equal to 2")


if __name__ == "__main__":
    try:
        valid_simulation()
        # unregistered_rfid()
        # test_testing_system()
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
        traceback.print_exc()

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
    LOGGER.setLevel(logging.DEBUG)
    RESULTS.display()
