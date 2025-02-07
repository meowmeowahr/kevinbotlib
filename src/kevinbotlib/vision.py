from abc import ABC, abstractmethod
import cv2
from cv2.typing import MatLike
import numpy as np

from kevinbotlib.comm import BinarySendable
import base64

class SingleFrameSendable(BinarySendable):
    encoding: str
    data_id: str = "kevinbotlib.vision.dtype.frame"

    def get_dict(self) -> dict:
        data = super().get_dict()
        data["encoding"] = self.encoding
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
        elif sendable.encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        else:
            raise ValueError(f"Unsupported encoding: {sendable.encoding}")

    @staticmethod
    def decode_base64(data: str, encoding: str) -> MatLike:
        buffer = base64.b64decode(data)
        if encoding == "JPG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        elif encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        else:
            raise ValueError(f"Unsupported encoding: {encoding}")

class BaseCamera(ABC):
    """Abstract class for creating Vision Cameras
    """
    @abstractmethod
    def get_frame() -> tuple[bool, MatLike]:
        pass

    @abstractmethod
    def set_resolution(width, height) -> None:
        pass


class CameraByIndex(BaseCamera):
    """Create an OpenCV camera from a device index

    Not recommended if you have more than one camera on a system
    """
    def __init__(self, index: int):
        self.capture = cv2.VideoCapture(index)

    def get_frame(self) -> tuple[bool, MatLike]:
        return self.capture.read()

class CameraByDevicePath(BaseCamera):
    """Create an OpenCV camera from a device path
    """
    def __init__(self, path: str):
        self.capture = cv2.VideoCapture(path)

    def get_frame(self) -> tuple[bool, MatLike]:
        return self.capture.read()
    
    def set_resolution(self, width: int, height: int) -> None:
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
