import cube_networking as cubenet
import cube_identification as cubeid
import time

class CubeBoxNetworking(cubenet.CubeNetworking):
    def __init__(self, node_name:str):
        super().__init__(node_name=node_name)

    #override
    def _main_loop(self):
        while self._keep_running:
            self.log.debug("CubeBoxNetworking main loop iteration")
            time.sleep(1)

if __name__ == "__main__":
    for i in range(1, cubeid.NB_CUBEBOXES + 1):
        cbnet = CubeBoxNetworking(f"CubeBox{i}")
        cbnet.discovery_response_loop()
        time.sleep(0.1)

