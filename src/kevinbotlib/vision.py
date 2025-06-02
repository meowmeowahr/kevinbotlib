from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Annotated, Any, ClassVar

import cv2
import numpy as np
import pybase64 as base64
from annotated_types import Len
from cv2.typing import MatLike

from kevinbotlib.comm import BinarySendable, RedisCommClient


class SingleFrameSendable(BinarySendable):
    """
    Sendable for a single frame of video or an image
    """

    encoding: str
    """Frame encoding format

    Supported encodings:
    * JPG
    * PNG
    """
    data_id: str = "kevinbotlib.vision.dtype.frame"
    """Internally used to differentiate sendable types"""
    struct: ClassVar[dict[str, Any]] = {
        "dashboard": [
            {"element": "value", "format": "limit:1024"},
            {"element": "resolution", "format": "raw"},
            {"element": "quality", "format": "raw"},
            {"element": "encoding", "format": "raw"},
        ]
    }
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["encoding"] = self.encoding
        return data


class MjpegStreamSendable(SingleFrameSendable):
    """
    Sendable for a single frame of an MJPG stream

    Contains all required information for decoding a video stream
    """

    data_id: str = "kevinbotlib.vision.dtype.mjpeg"
    """Internally used to differentiate sendable types"""
    quality: int
    """The current JPEG compression level out of 100 - lower means more compression"""
    resolution: Annotated[list[int], Len(min_length=2, max_length=2)]
    """A two integer list containing the video resolution (WIDTH x HEIGHT)"""
    encoding: str = "JPG"
    """Frame encoding format"""
    struct: ClassVar[dict[str, Any]] = {
        "dashboard": [
            {"element": "value", "format": "limit:1024"},
            {"element": "resolution", "format": "raw"},
            {"element": "quality", "format": "raw"},
            {"element": "encoding", "format": "raw"},
        ]
    }
    """Data structure _suggestion_ for use in dashboard applications"""

    def get_dict(self) -> dict:
        """Return the sendable in dictionary form

        Returns:
            dict: The sendable data
        """
        data = super().get_dict()
        data["quality"] = self.quality
        data["resolution"] = self.resolution
        return data


class FrameEncoders:
    """
    Encoders from OpenCV Mats into raw bytes or network sendables
    """

    @staticmethod
    def encode_sendable_jpg(frame: MatLike, quality: int = 80) -> SingleFrameSendable:
        """Encode an OpenCV Mat to a `SingleFrameSendable` using JPEG encoding

        Args:
            frame (MatLike): The Mat to encode
            quality (int, optional): The JPEG quality level. Defaults to 80.

        Returns:
            SingleFrameSendable: A sendable to be sent over the network
        """
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return SingleFrameSendable(value=base64.b64encode(buffer), encoding="JPG")

    @staticmethod
    def encode_sendable_png(frame: MatLike, compression: int = 3) -> SingleFrameSendable:
        """Encode an OpenCV Mat to a `SingleFrameSendable` using PNG encoding

        Args:
            frame (MatLike): The Mat to encode
            compression (int, optional): The PNG compression level. Defaults to 3.

        Returns:
            SingleFrameSendable: A sendable to be sent over the network
        """
        _, buffer = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, compression])
        return SingleFrameSendable(value=base64.b64encode(buffer), encoding="PNG")

    @staticmethod
    def encode_jpg(frame: MatLike, quality: int = 80) -> bytes:
        """Encode an OpenCV Mat to raw bytes using JPEG encoding

        Args:
            frame (MatLike): The Mat to encode
            quality (int, optional): The JPEG quality level. Defaults to 80.

        Returns:
            bytes: Raw data
        """
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer)

    @staticmethod
    def encode_png(frame: MatLike, compression: int = 3) -> bytes:
        """Encode an OpenCV Mat to raw bytes using PNG encoding

        Args:
            frame (MatLike): The Mat to encode
            compression (int, optional): The PNG compression level. Defaults to 3.

        Returns:
            bytes: Raw data
        """
        _, buffer = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, compression])
        return base64.b64encode(buffer)


class FrameDecoders:
    """
    Decoders from Base64 or network sendables to OpenCV Mats
    """

    @staticmethod
    def decode_sendable(sendable: SingleFrameSendable) -> MatLike:
        """Decode a SingleFrameSendable into an OpenCV Mat

        Args:
            sendable (SingleFrameSendable): The sendable to decode

        Raises:
            ValueError: If the encoding type isn't recognized

        Returns:
            MatLike: An OpenCV Mat
        """
        buffer = base64.b64decode(sendable.value)
        if sendable.encoding == "JPG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        if sendable.encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        msg = f"Unsupported encoding: {sendable.encoding}"
        raise ValueError(msg)

    @staticmethod
    def decode_base64(data: str, encoding: str) -> MatLike:
        """Decode a base64 string into an OpenCV Mat

        Args:
            data (str): The base64 data to decode
            encoding (str): The encoding format. Can be JPG or "PNG"

        Raises:
            ValueError: If the encoding type isn't recognized

        Returns:
            MatLike: An OpenCV Mat
        """
        buffer = base64.b64decode(data)
        if encoding == "JPG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        if encoding == "PNG":
            return cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_UNCHANGED)
        msg = f"Unsupported encoding: {encoding}"
        raise ValueError(msg)


class VisionCommUtils:
    """
    Various utilities to integrate vision data with networking
    """

    @staticmethod
    def init_comms_types(client: RedisCommClient) -> None:
        """Allows the use of frame data over the communication client

        Args:
            client (RedisCommClient): The communication client to integrate with
        """
        client.register_type(SingleFrameSendable)
        client.register_type(MjpegStreamSendable)


class BaseCamera(ABC):
    """Abstract class for creating Vision Cameras"""

    @abstractmethod
    def get_frame(self) -> tuple[bool, MatLike]:
        """Get the current frame from the camera

        Returns:
            tuple[bool, MatLike]: Frame retrieval success and an OpenCV Mat
        """

    @abstractmethod
    def set_resolution(self, width: int, height: int) -> None:
        """Attempt to set the current camera resolution

        Args:
            width (int): Frame width in px
            height (int): Frame height in px
        """


class CameraByIndex(BaseCamera):
    """Create an OpenCV camera from a device index

    Not recommended if you have more than one camera on a system
    """

    def __init__(self, index: int):
        """Initialize the camera

        Args:
            index (int): Index of the camera
        """
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
        """Initialize the camera

        Args:
            path (str): Device path of the camera ex: `/dev/video0`
        """
        self.capture = cv2.VideoCapture(path)

    def get_frame(self) -> tuple[bool, MatLike]:
        return self.capture.read()

    def set_resolution(self, width: int, height: int) -> None:
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


class VisionPipeline(ABC):
    """
    An abstract vision processing pipeline
    """

    def __init__(self, source: Callable[[], tuple[bool, MatLike]]) -> None:
        """Pipeline initialization

        Args:
            source (Callable[[], tuple[bool, MatLike]]): Getter for the frame to process
        """
        self.source = source

    @abstractmethod
    def run(*args, **kwargs) -> tuple[bool, MatLike | None]:
        """Runs the vision pipeline

        Returns:
            tuple[bool, MatLike | None]: An OpenCV Mat for pipeline visualization purposes. Can be ignored depending on the use case.
        """

    def return_values(self) -> Any:
        """Retrieves the calculations from the latest pipeline iteration

        Returns:
            Any: Pipeline calculations
        """


class EmptyPipeline(VisionPipeline):
    """
    A fake vision pipeline returning the original frame
    """

    def run(self) -> tuple[bool, MatLike]:
        """
        Fake pipeline. Return the inputs.

        Returns: Source values

        """
        return self.source()
