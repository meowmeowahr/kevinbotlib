from kevinbotlib.comm import KevinbotCommClient
from kevinbotlib.vision import CameraByIndex, EmptyPipeline, FrameEncoders, MjpegStreamSendable, VisionCommUtils

client = KevinbotCommClient()
VisionCommUtils.init_comms_types(client)

client.connect()
client.wait_until_connected()

camera = CameraByIndex(0)
camera.set_resolution(1920, 1080)

pipeline = EmptyPipeline(camera.get_frame)

while True:
    ok, frame = pipeline.run()
    if ok:
        encoded = FrameEncoders.encode_jpg(frame, 80)
        client.send("streams/camera0", MjpegStreamSendable(value=encoded, quality=80, resolution=frame.shape[:2]))
