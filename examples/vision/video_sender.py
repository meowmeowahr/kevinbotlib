from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.vision import FrameEncoders, SingleFrameSendable

import cv2

client = KevinbotCommClient()
client.register_type(SingleFrameSendable)

client.connect()
client.wait_until_connected()

cap = cv2.VideoCapture(0)

while True:
    ok, frame = cap.read()
    if ok:
        client.send("streams/camera0/frame", FrameEncoders.encode_sendable_png(frame, 0))
        print("here")