import time
import uuid
from kevinbotlib.comm import KevinbotCommInstance, ControlRights, SubTopic
from kevinbotlib.logger import Logger

class KevinbotServer:
    def __init__(self, host: str = "localhost", port: int = 1883, robot_topic: str = "kevinbot/") -> None:
        self.comms = KevinbotCommInstance(host, port, robot_topic, ControlRights.SERVER, f"kevinbotlib-server-{uuid.uuid4()}")
        

        self.logging_subtopic = SubTopic(self.comms, "logging")
        self.logger = Logger()
        self.logging_subtopic.attach_logger(self.logger)

        while True:
            time.sleep(5)


    def end(self):
        self.logger.info("Server shut down")


if __name__ == "__main__":
    import atexit
    server = KevinbotServer()
    atexit.register(server.end)
