import re
import socket
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Annotated, Any, ClassVar

import cv2
import numpy as np
import pybase64 as base64
import zmq
from annotated_types import Len
from cv2.typing import MatLike

from kevinbotlib.comm.abstract import (
    AbstractPubSubNetworkClient,
    AbstractSetGetNetworkClient,
)
from kevinbotlib.comm.sendables import BinarySendable
from kevinbotlib.logger import Logger
from kevinbotlib.robot import BaseRobot
from kevinbotlib.vision._sim import CamerasWindowView


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
    def init_comms_types(client: AbstractSetGetNetworkClient | AbstractPubSubNetworkClient) -> None:
        """Allows the use of frame data over the communication client

        Args:
            client (AbstractSetGetNetworkClient | AbstractPubSubNetworkClient): The communication client to integrate with
        """
        client.register_type(SingleFrameSendable)
        client.register_type(MjpegStreamSendable)


ZMQ_RECV_BUFFER_SIZE = 1024 * 1024


class BaseCamera(ABC):
    """Abstract class for creating Vision Cameras"""

    _SIM_REGISTERED_CAMERAS: ClassVar[list[str]] = []
    _SIM_ZMQ_PORT: ClassVar[int | None] = None

    def __init__(self, robot: BaseRobot | None):
        self.robot = robot

        if robot and robot.simulator:
            if not BaseCamera._SIM_REGISTERED_CAMERAS:
                robot.simulator.add_window("kevinbotlib.vision.cameras", CamerasWindowView)
            self._simulated = True
        else:
            self._simulated = False
        self._sim_camera_name: str | None = None
        self._resolution = (640, 480)
        self._fps = 60
        self._sim_frame = np.zeros((self.resolution[0], self.resolution[1], 3), dtype=np.uint8)
        self._sim_zmq: zmq.Context | None = None
        self._sim_zmq_socket: zmq.Socket | None = None

    def __init_sim__(self, camera_name: str) -> None:
        """
        Initialize the simulator window.

        Simulator camera name must be registered using simulator_register_camera_name() before this.

        This method is for internal use within a camera implementation.
        """
        if self.simulated:
            BaseCamera._SIM_REGISTERED_CAMERAS.append(camera_name)
            self._sim_camera_name = camera_name

            # create a zmq context
            self._sim_zmq = zmq.Context()
            self._sim_zmq_socket = self._sim_zmq.socket(zmq.SUB)
            if not BaseCamera._SIM_ZMQ_PORT:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", 0))  # 0 = request ephemeral port
                    port = s.getsockname()[1]
                    Logger().debug(f"Simulator: Camera streaming ZMQ port: {port}")
                    BaseCamera._SIM_ZMQ_PORT = port
            self._sim_zmq_socket.connect(f"tcp://127.0.0.1:{BaseCamera._SIM_ZMQ_PORT}")
            self._sim_zmq_socket.subscribe(re.sub(r"[^A-Za-z0-9-_]", "_", self._sim_camera_name))
            self._sim_zmq_socket.setsockopt(zmq.RCVBUF, ZMQ_RECV_BUFFER_SIZE)
            self.robot.simulator.send_to_window(
                "kevinbotlib.vision.cameras", {"type": "port", "port": BaseCamera._SIM_ZMQ_PORT}
            )

            def sim_frame_recv_loop():
                while True:
                    parts = self._sim_zmq_socket.recv_multipart()
                    if len(parts) != 2:  # noqa: PLR2004
                        Logger().warning("Invalid frame data received from simulator")
                        continue

                    image_bytes = parts[1]
                    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
                    self._sim_frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            threading.Thread(target=sim_frame_recv_loop, daemon=True, name="KevinbotLib.Vision.SimIO.FrameRecv").start()

            self.robot.simulator.send_to_window("kevinbotlib.vision.cameras", {"type": "new", "name": camera_name})

            self.robot.simulator.send_to_window(
                "kevinbotlib.vision.cameras",
                {"type": "fps", "fps": self._fps, "name": self._sim_camera_name},
            )
            self.robot.simulator.send_to_window(
                "kevinbotlib.vision.cameras", {"type": "res", "res": self.resolution, "name": self._sim_camera_name}
            )

    @abstractmethod
    def get_frame(self) -> tuple[bool, MatLike]:
        """
        Get the current frame from the camera. Method is blocking until a frame is available.

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
        self._resolution = (width, height)
        if not self.simulated:
            return
        self.robot.simulator.send_to_window(
            "kevinbotlib.vision.cameras", {"type": "res", "res": (width, height), "name": self._sim_camera_name}
        )

    @property
    def resolution(self) -> tuple:
        """
        Get the current camera resolution

        Returns:
            Width x Height
        """
        return self._resolution

    def set_frame_rate(self, fps: int) -> None:
        """
        Set the current camera frame rate.

        Args:
            fps: Frame rate
        """
        self._fps = fps
        if not self.simulated:
            return
        self.robot.simulator.send_to_window(
            "kevinbotlib.vision.cameras", {"type": "fps", "fps": fps, "name": self._sim_camera_name}
        )

    @property
    def fps(self) -> int:
        """
        Get the current camera frame rate.

        Returns:
            FPS
        """
        return self._fps

    @property
    def simulated(self) -> bool:
        """
        Is the camera simulated? Should be used in all cameras to disable hardware connections.

        Returns:
            Running in simulator?
        """
        return self._simulated


class CameraByIndex(BaseCamera):
    """Create an OpenCV camera from a device index

    Not recommended if you have more than one camera on a system
    """

    def __init__(self, robot: BaseRobot | None, index: int):
        """Initialize the camera

        Args:
            index (int): Index of the camera
        """
        super().__init__(robot)

        if not self.simulated:
            self.capture = cv2.VideoCapture(index)
            self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*"MJPG"))
            self.capture.set(cv2.CAP_PROP_FPS, self.fps)

        super().__init_sim__(
            f"Index: {index}"
        )  # Initialize the camera simulation window. Must be called after simulator_register_camera_name()

    def get_frame(self) -> tuple[bool, MatLike]:
        """Get the current frame from the camera. Method is blocking until a frame is available.

        Returns:
            tuple[bool, MatLike]: Frame retrieval success and an OpenCV Mat
        """
        if not self.simulated:
            return self.capture.read()
        return True, self._sim_frame

    def set_resolution(self, width: int, height: int) -> None:
        """Attempt to set the current camera resolution

        Args:
            width (int): Frame width in px
            height (int): Frame height in px
        """
        super().set_resolution(width, height)
        if not self.simulated:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def set_frame_rate(self, fps: int) -> None:
        """
        Set the current camera frame rate.

        Args:
            fps: Frame rate
        """
        super().set_frame_rate(fps)
        if not self.simulated:
            self.capture.set(cv2.CAP_PROP_FPS, fps)


class CameraByDevicePath(BaseCamera):
    """Create an OpenCV camera from a device path"""

    def __init__(self, robot: BaseRobot | None, path: str):
        """Initialize the camera

        Args:
            path (str): Device path of the camera ex: `/dev/video0`
        """
        super().__init__(robot)

        if not self.simulated:
            self.capture = cv2.VideoCapture(path)
        self.set_resolution(*self.resolution)

        super().__init_sim__(path)

    def get_frame(self) -> tuple[bool, MatLike]:
        """Get the current frame from the camera. Method is blocking until a frame is available.

        Returns:
            tuple[bool, MatLike]: Frame retrieval success and an OpenCV Mat
        """
        super().get_frame()
        if not self.simulated:
            return self.capture.read()
        return True, self._sim_frame

    def set_resolution(self, width: int, height: int) -> None:
        """Attempt to set the current camera resolution

        Args:
            width (int): Frame width in px
            height (int): Frame height in px
        """
        super().set_resolution(width, height)
        if not self.simulated:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def set_frame_rate(self, fps: int) -> None:
        """
        Set the current camera frame rate.

        Args:
            fps: Frame rate
        """
        super().set_frame_rate(fps)
        if not self.simulated:
            self.capture.set(cv2.CAP_PROP_FPS, fps)


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
    def run(self, *args, **kwargs) -> tuple[bool, MatLike | None]:
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
