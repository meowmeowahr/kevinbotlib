from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Annotated, Any, ClassVar

import cv2
import numpy as np
import pybase64 as base64
from annotated_types import Len
from cv2.typing import MatLike

from kevinbotlib.comm import BinarySendable, KevinbotCommClient


class SingleFrameSendable(BinarySendable):
    encoding: str
    data_id: str = "kevinbotlib.vision.dtype.frame"

    def get_dict(self) -> dict:
        data = super().get_dict()
        data["encoding"] = self.encoding
        return data


class MjpegStreamSendable(SingleFrameSendable):
    data_id: str = "kevinbotlib.vision.dtype.mjpeg"
    quality: int
    resolution: Annotated[list[int], Len(min_length=2, max_length=2)]
    encoding: str = "JPG"
    struct: ClassVar[dict[str, Any]] = {
        "dashboard": [
            {"element": "value", "format": "limit:1024"},
            {"element": "resolution", "format": "raw"},
            {"element": "quality", "format": "raw"},
            {"element": "encoding", "format": "raw"},
        ]
    }

    def get_dict(self) -> dict:
        data = super().get_dict()
        data["quality"] = self.quality
        data["resolution"] = self.resolution
        return data


class FrameEncoders:
    """
    Encoders from OpenCV Mats to Base64
    """

    @staticmethod
    def encode_sendable_jpg(frame: MatLike, quality: int = 80) -> SingleFrameSendable:
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return SingleFrameSendable(value=base64.b64encode(buffer), encoding="JPG")

    @staticmethod
    def encode_sendable_png(frame: MatLike, compression: int = 3) -> SingleFrameSendable:
        _, buffer = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, compression])
        return SingleFrameSendable(value=base64.b64encode(buffer), encoding="PNG")

    @staticmethod
    def encode_jpg(frame: MatLike, quality: int = 80) -> bytes:
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer)

    @staticmethod
    def encode_png(frame: MatLike, compression: int = 3) -> bytes:
        _, buffer = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, compression])
        return base64.b64encode(buffer)


class FrameDecoders:
    """
    Decoders from Base64 to OpenCV Mats
    """

    @staticmethod
    def decode_sendable(sendable: SingleFrameSendable) -> MatLike:
        buffer = base64.b64decode(sendable.value)
        if sendable.encoding == "JPG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        if sendable.encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        msg = f"Unsupported encoding: {sendable.encoding}"
        raise ValueError(msg)

    @staticmethod
    def decode_base64(data: str, encoding: str) -> MatLike:
        buffer = base64.b64decode(data)
        if encoding == "JPG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        if encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        msg = f"Unsupported encoding: {encoding}"
        raise ValueError(msg)


class VisionCommUtils:
    @staticmethod
    def init_comms_types(client: KevinbotCommClient) -> None:
        client.register_type(SingleFrameSendable)
        client.register_type(MjpegStreamSendable)


class BaseCamera(ABC):
    """Abstract class for creating Vision Cameras"""

    @abstractmethod
    def get_frame(self) -> tuple[bool, MatLike]:
        pass

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> None:
        pass


class CameraByIndex(BaseCamera):
    """Create an OpenCV camera from a device index

    Not recommended if you have more than one camera on a system
    """

    def __init__(self, index: int):
        self.capture = cv2.VideoCapture(index)
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
        self.capture.set(cv2.CAP_PROP_FPS, 60)

    def get_frame(self) -> tuple[bool, MatLike]:
        return self.capture.read()

    def set_resolution(self, width: int, height: int) -> None:
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


class CameraByDevicePath(BaseCamera):
    """Create an OpenCV camera from a device path"""

    def __init__(self, path: str):
        self.capture = cv2.VideoCapture(path)

    def get_frame(self) -> tuple[bool, MatLike]:
        return self.capture.read()

    def set_resolution(self, width: int, height: int) -> None:
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


class VisionPipeline(ABC):
    def __init__(self, source: Callable[[], tuple[bool, MatLike]]) -> None:
        self.source = source

    @abstractmethod
    def run(*args, **kwargs) -> tuple[bool, MatLike | None]:
        pass

    def return_values(self) -> Any:
        pass


class EmptyPipeline(VisionPipeline):
    def run(self) -> tuple[bool, MatLike]:
        return self.source()
