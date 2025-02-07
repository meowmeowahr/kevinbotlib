from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.vision import FrameEncoders, SingleFrameSendable, CameraByDevicePath

client = KevinbotCommClient()
client.register_type(SingleFrameSendable)

client.connect()
client.wait_until_connected()

camera = CameraByDevicePath("/dev/video0")
camera.set_resolution(1280, 720)

while True:
    ok, frame = camera.get_frame()
    if ok:
        client.send("streams/camera0/frame", FrameEncoders.encode_sendable_png(frame, 0))