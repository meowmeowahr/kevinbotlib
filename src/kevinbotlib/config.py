"""
Configuration manager for KevinbotLib
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from loguru import logger
from platformdirs import site_config_dir, user_config_dir


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

    def __init__(self):
        # Set paths for user and system-wide configuration
        self.user_config_path = Path(user_config_dir("kevinbotlib")) / "settings.yaml"
        self.system_config_path = Path(site_config_dir("kevinbotlib")) / "settings.yaml"

        # Load configuration with fallback to defaults
        self.config = self._load_config()

        # Set default values if missing
        self._validate_mqtt_config()

    def _load_config(self) -> dict:
        """Loads the config from user or system file, or returns an empty dict if not found."""
        if self.user_config_path.exists():
            logger.info(f"Loading user config from {self.user_config_path}")
            with open(self.user_config_path) as f:
                return yaml.safe_load(f) or {}
        elif self.system_config_path.exists():
            logger.info(f"Loading system config from {self.system_config_path}")
            with open(self.system_config_path) as f:
                return yaml.safe_load(f) or {}
        else:
            logger.warning("No config found, using defaults.")
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
        self._save_config()

    def _save_config(self):
        """Save the configuration to the user"""
        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.user_config_path, "w") as f:
            yaml.dump(self.config, f)
        logger.info(f"Configuration saved to {self.user_config_path}")
