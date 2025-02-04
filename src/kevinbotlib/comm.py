from typing import Any, Type, TypeVar
import time
import json
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import uuid
from pydantic import BaseModel, ConfigDict
from enum import IntEnum
import orjson
import atexit

from kevinbotlib.logger import Logger as _Logger


class ControlRights(IntEnum):
    SERVER = 0
    USER = 1
    ALL = 2


class SendableDataType(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    title: str
    value: Any
    rights: ControlRights = ControlRights.ALL
    last_sender: str = "unknown"
    extras: dict = {}

    def __str__(self) -> str:
        return f"{self.value}"

class IntegerData(SendableDataType):
    value: int

class FloatData(SendableDataType):
    value: float

class StringData(SendableDataType):
    value: str

class BooleanData(SendableDataType):
    value: bool

class DictData(SendableDataType):
    value: dict

T = TypeVar("T", bound=SendableDataType)


class KevinbotCommInstance:
    def __init__(self, broker="localhost", port=1883, topic_prefix="kevinbot/", rights: ControlRights = ControlRights.USER, client_id: str = f"kevinbotlib-{uuid.uuid4()}"):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.rights = rights
        self._cid = client_id

        self.logger = _Logger()

        self._client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id=client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(self.broker, self.port, 60)
        
        self.data_store: dict[str, SendableDataType] = {}
        
        self.lock = threading.Lock()
        
        self._client.loop_start()
        while not self._client.is_connected():
            time.sleep(0.1)

        atexit.register(self.close)

    def _on_connect(self, _: mqtt.Client, __, ___, reason_code, ____):
        """Subscribe to all topics under the given prefix when connected."""
        self._client.subscribe(f"{self.topic_prefix}#")
        self._client.publish(f"{self.topic_prefix}%clients/connect", self._cid)
        self.logger.info(f"Connected to mqtt with rc={reason_code}")

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """Handle incoming messages and store the latest values."""
        try:
            full_topic = msg.topic
            if "%" in full_topic:
                return
            
            payload = json.loads(msg.payload.decode())
            if not full_topic.startswith(self.topic_prefix):
                return
                
            relative_topic = full_topic[len(self.topic_prefix):]
            topic_parts = relative_topic.split('/')

            if len(topic_parts) < 2:
                self.logger.error(f"Got malformed data: expected topic depth of at least 2, got {len(topic_parts)}")
                return

            key = topic_parts[0]
            attribute = topic_parts[1]
            
            with self.lock:
                if key not in self.data_store:
                    self.data_store[key] = SendableDataType(title=key, value=None)

                if attribute == "rights":
                    payload = ControlRights(int(payload))
                elif attribute == "type":
                    self.data_store[key].extras["type"] = payload
                else:
                    setattr(self.data_store[key], attribute, payload)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")


    def _loguru_sink(self, message):
        """Custom sink to send Loguru messages via MQTT."""
        message = json.loads(message)
        log_entry = {
            "time": message["record"]["time"]["repr"],
            "level": message["record"]["level"]["name"],
            "message": message["record"]["message"],
            "file": message["record"]["file"]["name"],
            "line": message["record"]["line"],
            "cid": self._cid
        }
        self.send("entry", DictData(title="Latest Log Entry", value=log_entry))

    def attach_logger(self, logger: _Logger):
        logger._internal_logger.add(self._loguru_sink, level=logger.level.name, serialize=True)

    def send(self, key: str | uuid.UUID, data: SendableDataType):
        """Send a value to the MQTT broker with a specified data type."""
        if isinstance(key, uuid.UUID):
            key = str(key)

        payload = data.model_dump()
        payload["last_sender"] = self._cid
        with self.lock:
            self.data_store[key] = data

        for attr, val in payload.items():
            self._client.publish(f"{self.topic_prefix}{key}/{attr}", orjson.dumps(val))

    def get(self, key: str | uuid.UUID, data_type: Type[T]) -> T | None:
        """Retrieve the latest value for a given key, ensuring correct casting."""
        if isinstance(key, uuid.UUID):
            key = str(key)
        
        with self.lock:
            if key in self.data_store:
                data = self.data_store[key]
                return data_type(**data.model_dump())
        return None
    
    @property
    def mqtt_client(self) -> mqtt.Client:
        return self._client

    def close(self):
        """Close the MQTT client connection."""
        self.logger.info("Closing down mqtt client")
        self._client.publish(f"{self.topic_prefix}%clients/disconnect", self._cid).wait_for_publish()
        self._client.loop_stop()
        self._client.disconnect()

class SubTopic:
    def __init__(self, parent_instance: KevinbotCommInstance, sub_topic: str):
        """
        Initialize a sub-channel using the parent channel's client with a different topic prefix.
        
        Args:
            parent_channel: The parent KevinbotCommChannel instance
            sub_topic: The sub-topic prefix (e.g., "sensors/" or "controls/")
        """
        self.parent = parent_instance
        # Ensure sub_topic ends with a forward slash
        self.sub_topic = sub_topic if sub_topic.endswith('/') else f"{sub_topic}/"
        # Combine parent's topic prefix with sub-topic
        self.topic_prefix = f"{parent_instance.topic_prefix}{self.sub_topic}"
        # Create a separate data store for the sub-channel
        self.data_store: dict[str, SendableDataType] = {}
        self.lock = threading.Lock()
        
        # Subscribe to sub-channel topics
        self.parent._client.message_callback_add(
            f"{self.topic_prefix}#",
            self._on_message
        )
        self.parent._client.subscribe(f"{self.topic_prefix}#")

    def _on_message(self, client: mqtt.Client, userdata, msg):
        """Handle incoming messages specific to this sub-channel."""
        try:
            if msg.topic.startswith("%"):
                return
            
            payload = json.loads(msg.payload.decode())
            if not msg.topic.startswith(self.topic_prefix):
                return
                
            relative_topic = msg.topic[len(self.topic_prefix):]
            topic_parts = relative_topic.split('/')

            if len(topic_parts) < 2:
                self.parent.logger.error(f"Got malformed data: expected topic depth of at least 2, got {len(topic_parts)}")
                return

            key = topic_parts[0]
            attribute = topic_parts[1]
            
            with self.lock:
                if key not in self.data_store:
                    self.data_store[key] = SendableDataType(title=key, value=None)

                if attribute == "rights":
                    payload = ControlRights(int(payload))
                elif attribute == "type":
                    self.data_store[key].extras["type"] = payload
                else:
                    setattr(self.data_store[key], attribute, payload)
        except Exception as e:
            self.parent.logger.error(f"Error processing message in sub-channel: {e}")

    def _loguru_sink(self, message):
        """Custom sink to send Loguru messages via MQTT."""
        message = json.loads(message)
        log_entry = {
            "time": message["record"]["time"]["repr"],
            "level": message["record"]["level"]["name"],
            "message": message["record"]["message"],
            "file": message["record"]["file"]["name"],
            "line": message["record"]["line"],
            "cid": self.parent._cid
        }
        self.send("entry", DictData(title="Latest Log Entry", value=log_entry))

    def attach_logger(self, logger: _Logger):
        logger._internal_logger.add(self._loguru_sink, level=logger.level.name, serialize=True)


    def send(self, key: str | uuid.UUID, data: SendableDataType):
        """Send data through the sub-channel."""
        if isinstance(key, uuid.UUID):
            key = str(key)

        payload = data.model_dump()
        payload["last_sender"] = self.parent._cid
        with self.lock:
            self.data_store[key] = data

        for attr, val in payload.items():
            self.parent._client.publish(f"{self.topic_prefix}{key}/{attr}", orjson.dumps(val))

    def get(self, key: str | uuid.UUID, data_type: Type[T]) -> T | None:
        """Retrieve data from the sub-channel's data store."""
        if isinstance(key, uuid.UUID):
            key = str(key)
        
        with self.lock:
            if key in self.data_store:
                data = self.data_store[key]
                return data_type(**data.model_dump())
        return None
