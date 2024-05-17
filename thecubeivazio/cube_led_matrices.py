# TODO: add imports and test method

from cube_common_defines import *

class CubeMasterLedMatrices:
    # TODO: set this in a config file
    NB_MATRICES = 10
    def __init__(self):
        raise NotImplementedError

    def display_text_on_matrix(self, matrix_id:int, text:str):
        raise NotImplementedError

    def team_name_to_matrix_id(self, team_name:str) -> int:
        raise NotImplementedError



# TODO: test display
if __name__ == "__main__":
    raise NotImplementedError
