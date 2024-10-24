"""
Configuration manager for KevinbotLib
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml
from loguru import logger
from platformdirs import site_config_dir, user_config_dir


class ConfigLocation(Enum):
    """Enum to represent the location of the config file"""

    USER = "user"
    SYSTEM = "system"
    AUTO = "auto"


@dataclass
class MqttConfig:
    """MQTT configuration"""

    host: str
    port: int
    keepalive: int

    def __setattr__(self, key, value):
        """Allow setting attributes directly."""
        super().__setattr__(key, value)


class KevinbotConfig:
    """Handle Kevinbot configuration changes"""

    def __init__(self, location: ConfigLocation = ConfigLocation.AUTO):
        self.config_location = location

        # Set paths for user and system-wide configuration
        self.user_config_path = Path(user_config_dir("kevinbotlib")) / "settings.yaml"
        self.system_config_path = Path(site_config_dir("kevinbotlib")) / "settings.yaml"

        # Choose the appropriate config path based on location
        self.config_path = self._get_config_path()

        # Load configuration with fallback to defaults
        self.config = self._load_config()

        # Set default values if missing
        self._validate_mqtt_config()

    def _get_config_path(self) -> Path:
        """Determine the correct config path based on the provided location."""
        if self.config_location == ConfigLocation.USER:
            return self.user_config_path
        if self.config_location == ConfigLocation.SYSTEM:
            return self.system_config_path
        if self.user_config_path.exists():
            return self.user_config_path
        if self.system_config_path.exists():
            return self.system_config_path
        return self.user_config_path

    def _load_config(self) -> dict:
        """Loads the config from user or system file, or returns an empty dict if not found."""
        if self.config_path.exists():
            logger.info(f"Loading config from {self.config_path}")
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning(f"No config found at {self.config_path}, using defaults.")
            return {}

    def _validate_mqtt_config(self):
        """Ensure that default values for MQTT config are present."""
        if "mqtt" not in self.config:
            self.config["mqtt"] = {}
        if "host" not in self.config["mqtt"]:
            self.config["mqtt"]["host"] = "localhost"
            logger.warning("MQTT host missing, defaulting to 'localhost'.")
        if "port" not in self.config["mqtt"]:
            self.config["mqtt"]["port"] = 1883
            logger.warning("MQTT port missing, defaulting to 1883.")
        if "keepalive" not in self.config["mqtt"]:
            self.config["mqtt"]["keepalive"] = 60
            logger.warning("MQTT keepalive missing, defaulting to 60.")

    @property
    def mqtt(self) -> MqttConfig:
        """Get the mqtt configuration

        Returns:
            MqttConfig: `MqttConfig` object
        """
        return MqttConfig(
            host=self.config["mqtt"]["host"],
            port=self.config["mqtt"]["port"],
            keepalive=self.config["mqtt"]["keepalive"],
        )

    @mqtt.setter
    def mqtt(self, new_config: MqttConfig):
        """Set the mqtt configuration

        Args:
            new_config (MqttConfig): Mqtt configurations
        """
        self.config["mqtt"]["host"] = new_config.host
        self.config["mqtt"]["port"] = new_config.port
        self.config["mqtt"]["keepalive"] = new_config.keepalive
        self._save_config()

    def _save_config(self):
        """Save the configuration to the selected location"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f)
        logger.info(f"Configuration saved to {self.config_path}")
