from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.vision import MjpegStreamSendable, FrameDecoders, VisionCommUtils

import cv2

client = KevinbotCommClient()
VisionCommUtils.init_comms_types(client)

client.connect()
client.wait_until_connected()

try:
    while True:
        sendable = client.get("streams/camera0", MjpegStreamSendable)  # noqa: T201
        if sendable:
            cv2.imshow("image", FrameDecoders.decode_sendable(sendable))
        cv2.waitKey(1)
except KeyboardInterrupt:
    client.disconnect()
