import uuid
from kevinbotlib.comm import KevinbotCommInstance, ControlRights

class KevinbotServer:
    def __init__(self, host: str = "localhost", port: int = 1883, robot_topic: str = "kevinbot/") -> None:
        self.comms = KevinbotCommInstance(host, port, robot_topic, ControlRights.SERVER, f"kevinbotlib-server-{uuid.uuid4()}")

    def end(self):
        self.comms.close()


if __name__ == "__main__":
    import atexit
    server = KevinbotServer()
    atexit.register(server.end)
