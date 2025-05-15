from kevinbotlib.comm import RedisCommClient
from kevinbotlib.logger import FileLoggerConfig, Logger, LoggerConfiguration
from kevinbotlib.vision import (
    CameraByIndex,
    EmptyPipeline,
    FrameEncoders,
    MjpegStreamSendable,
    VisionCommUtils,
)

logger = Logger()
logger.configure(LoggerConfiguration(file_logger=FileLoggerConfig()))

client = RedisCommClient()
VisionCommUtils.init_comms_types(client)

client.connect()
client.wait_until_connected()

camera = CameraByIndex(0)
camera.set_resolution(1920, 1080)

pipeline = EmptyPipeline(camera.get_frame)

while True:
    ok, frame = pipeline.run()
    if ok:
        encoded = FrameEncoders.encode_jpg(frame, 100)
        client.set(
            "streams/camera0",
            MjpegStreamSendable(value=encoded, quality=100, resolution=frame.shape[:2]),
        )
        client.set(
            "streams/camera1",
            MjpegStreamSendable(value=encoded, quality=100, resolution=frame.shape[:2]),
        )
