"""
Configuration manager for KevinbotLib
"""

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from platformdirs import site_config_dir, user_config_dir


class ConfigLocation(Enum):
    """Enum to represent the location of the config file"""

    USER = "user"
    SYSTEM = "system"
    AUTO = "auto"
    NONE = "none"
    MANUAL = "manual"


class _MQTT:
    def __init__(self, data: dict[str, Any], config: "KevinbotConfig"):
        self._config = config
        self._data = data

    @property
    def port(self):
        return self._data.get("port", 1883)

    @port.setter
    def port(self, value: int):
        self._data["port"] = value
        self._config.save()

    @property
    def host(self):
        return self._data.get("host", "localhost")

    @host.setter
    def host(self, value: str):
        self._data["host"] = value
        self._config.save()

    @property
    def keepalive(self):
        return self._data.get("keepalive", 60)

    @keepalive.setter
    def keepalive(self, value: int):
        self._data["keepalive"] = value
        self._config.save()

    @property
    def data(self):
        return {"port": self.port, "host": self.host, "keepalive": self.keepalive}


class _Core:
    def __init__(self, data: dict[str, Any], config: "KevinbotConfig"):
        self._config = config
        self._data = data

    @property
    def port(self) -> str:
        return self._data.get("port", "/dev/ttyAMA2")

    @port.setter
    def port(self, value: str):
        self._data["port"] = value
        self._config.save()

    @property
    def baud(self) -> int:
        return self._data.get("baud", 921600)

    @baud.setter
    def baud(self, value: int):
        self._data["baud"] = value
        self._config.save()

    @property
    def handshake_timeout(self) -> float:
        return self._data.get("handshake_timeout", 5.0)

    @handshake_timeout.setter
    def handshake_timeout(self, value: int):
        self._data["handshake_timeout"] = value
        self._config.save()

    @property
    def timeout(self) -> float:
        return self._data.get("timeout", 5.0)

    @timeout.setter
    def timeout(self, value: int):
        self._data["timeout"] = value
        self._config.save()

    @property
    def tick(self) -> float:
        return self._data.get("tick", 1)

    @tick.setter
    def tick(self, value: float):
        self._data["tick"] = value
        self._config.save()

    @property
    def data(self):
        return {
            "port": self.port,
            "baud": self.baud,
            "handshake_timeout": self.handshake_timeout,
            "timeout": self.timeout,
            "tick": self.tick,
        }


class _XBee:
    def __init__(self, data: dict[str, Any], config: "KevinbotConfig"):
        self._config = config
        self._data = data

    @property
    def port(self) -> str:
        return self._data.get("port", "/dev/ttyAMA0")

    @port.setter
    def port(self, value: str):
        self._data["port"] = value
        self._config.save()

    @property
    def baud(self) -> int:
        return self._data.get("baud", 921600)

    @baud.setter
    def baud(self, value: int):
        self._data["baud"] = value
        self._config.save()

    @property
    def timeout(self) -> float:
        return self._data.get("timeout", 5.0)

    @timeout.setter
    def timeout(self, value: int):
        self._data["timeout"] = value
        self._config.save()

    @property
    def api(self) -> int:
        return self._data.get("api", 2)

    @api.setter
    def api(self, value: int):
        self._data["api"] = value
        self._config.save()

    @property
    def data(self):
        return {"port": self.port, "baud": self.baud, "timeout": self.timeout, "api": self.api}


class _Server:
    def __init__(self, data: dict[str, Any], config: "KevinbotConfig"):
        self._config = config
        self._data = data

    @property
    def root_topic(self):
        return self._data.get("root_topic", "kevinbot")

    @root_topic.setter
    def root_topic(self, value: int):
        self._data["root_topic"] = value
        self._config.save()

    @property
    def data(self):
        return {"root_topic": self.root_topic}


class KevinbotConfig:
    def __init__(self, location: ConfigLocation = ConfigLocation.AUTO, path: str | Path | None = None):
        self.config_location = location

        self.user_config_path = Path(user_config_dir("kevinbotlib")) / "settings.yaml"
        self.system_config_path = Path(site_config_dir("kevinbotlib")) / "settings.yaml"

        self.manual_path: Path | None = None
        if path:
            self.manual_path = Path(path)

        self.config_path = self._get_config_path()

        self.config: dict = {}

        self.mqtt: _MQTT = _MQTT({}, self)
        self.core: _Core = _Core({}, self)
        self.xbee: _XBee = _XBee({}, self)
        self.server: _Server = _Server({}, self)

        self.load()

    def _get_config_path(self) -> Path | None:
        """Get the optimal configuration path

        Returns:
            Path | None: File location
        """
        if self.config_location == ConfigLocation.NONE:
            return None
        if self.config_location == ConfigLocation.MANUAL:
            if self.manual_path:
                return Path(self.manual_path)
            logger.warning("ConfigLocation.MANUAL set without config path, defaulting to ConfigLocation.NONE")
            return None  # should never happen
        if self.config_location == ConfigLocation.USER:
            return self.user_config_path
        if self.config_location == ConfigLocation.SYSTEM:
            return self.system_config_path
        # AUTO: Prefer user, else system, if none, return user
        if self.user_config_path.exists():
            return self.user_config_path
        if self.system_config_path.exists():
            return self.system_config_path
        return self.user_config_path

    def load(self) -> None:
        if self.config_path and self.config_path.exists():
            with open(self.config_path) as file:
                self.config = yaml.safe_load(file) or {}

        self.mqtt = _MQTT(self.config.get("mqtt", {}), self)
        self.core = _Core(self.config.get("core", {}), self)
        self.xbee = _XBee(self.config.get("xbee", {}), self)
        self.server = _Server(self.config.get("server", {}), self)

    def save(self) -> None:
        if self.config_path:
            with open(self.config_path, "w") as file:
                yaml.dump(self._get_data(), file, default_flow_style=False)
        else:
            logger.error("Couldn't save configuration to empty path")

    def dump(self) -> str:
        """Dump configuration

        Returns:
            str: YAML
        """
        return yaml.dump(self._get_data(), default_flow_style=False)

    def _get_data(self):
        return {
            "mqtt": self.mqtt.data,
            "core": self.core.data,
            "xbee": self.xbee.data,
            "server": self.server.data,
        }

    def __repr__(self):
        return f"{super().__repr__()}\n\n{yaml.dump(self._get_data(), default_flow_style=False)}"
