import time

from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.vision import SingleFrameSendable, FrameDecoders

import cv2

client = KevinbotCommClient(on_update=None)
client.register_type(SingleFrameSendable)
client.connect()
client.wait_until_connected()

try:
    while True:
        sendable = client.get("streams/camera0/frame", SingleFrameSendable)  # noqa: T201
        if sendable:
            cv2.imshow("image", FrameDecoders.decode_sendable(sendable))
        cv2.waitKey(1)
except KeyboardInterrupt:
    client.disconnect()
