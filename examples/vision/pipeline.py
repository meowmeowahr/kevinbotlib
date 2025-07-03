from collections.abc import Callable
from typing import Any

import cv2
from cv2.typing import MatLike

from kevinbotlib.logger import Logger, LoggerConfiguration
from kevinbotlib.vision import CameraByIndex, VisionPipeline

Logger().configure(LoggerConfiguration())

camera = CameraByIndex(None, 0)


class MyPipeline(VisionPipeline):
    def __init__(self, source: Callable[[], tuple[bool, MatLike]]):
        super().__init__(source)

    def run(self) -> tuple[bool, MatLike | None]:
        # convert to grayscale as an example
        inp = self.input_frame
        return inp[0], cv2.cvtColor(inp[1], cv2.COLOR_BGR2GRAY)

    def return_values(self) -> Any:
        return None


while True:
    pipeline = MyPipeline(camera.get_frame)
    ok, frame = pipeline.run()
    if ok:
        cv2.imshow("image", frame)
    if cv2.waitKey(1) == ord("q"):
        break
