# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from kevinbotlib.config import ConfigLocation, KevinbotConfig


def test_manual_path(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    assert config.config_path == tmp_path.joinpath("config.yaml")

    config = KevinbotConfig(ConfigLocation.MANUAL)
    assert config.config_path is None


def test_no_path():
    config = KevinbotConfig(ConfigLocation.NONE)
    assert config.config_path is None


def test_system_path():
    config = KevinbotConfig(ConfigLocation.SYSTEM)
    assert isinstance(config.config_path, Path)


def test_user_path():
    config = KevinbotConfig(ConfigLocation.USER)
    assert isinstance(config.config_path, Path)


def test_auto_system_path(monkeypatch, tmp_path: Path):
    (tmp_path / "settings.yaml").touch()
    monkeypatch.setattr("kevinbotlib.config.user_config_dir", lambda _: Path("/nonexistent"))
    monkeypatch.setattr("kevinbotlib.config.site_config_dir", lambda _: tmp_path)
    config = KevinbotConfig(ConfigLocation.AUTO)
    assert isinstance(config.config_path, Path)


def test_auto_no_path(monkeypatch):
    monkeypatch.setattr("kevinbotlib.config.user_config_dir", lambda _: Path("/nonexistent"))
    monkeypatch.setattr("kevinbotlib.config.site_config_dir", lambda _: Path("/nonexistent"))
    config = KevinbotConfig(ConfigLocation.AUTO)
    assert isinstance(config.config_path, Path)


def test_auto_user_path():
    config = KevinbotConfig(ConfigLocation.AUTO)
    assert isinstance(config.config_path, Path)


def test_save(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    config.save()

    with open(tmp_path.joinpath("config.yaml")) as f:
        assert f.read() != ""  # File isn't empty anymore


def test_save_none():
    config = KevinbotConfig(ConfigLocation.NONE)
    config.save()


def test_dump():
    config = KevinbotConfig(ConfigLocation.NONE)
    assert isinstance(config.dump(), str)


def test_repr():
    config = KevinbotConfig(ConfigLocation.NONE)
    assert "localhost" in config.__repr__()


def test_mqtt(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    assert config.mqtt.host == "localhost"
    assert config.mqtt.port == 1883
    assert config.mqtt.keepalive == 60

    config.mqtt.host = "127.0.0.1"
    assert config.mqtt.host == "127.0.0.1"

    config.mqtt.port = 2883
    assert config.mqtt.port == 2883

    config.mqtt.keepalive = 30
    assert config.mqtt.keepalive == 30


def test_core(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    assert config.core.baud == 921600
    assert config.core.port == "/dev/ttyAMA2"
    assert config.core.tick == 1
    assert config.core.timeout == 5
    assert config.core.handshake_timeout == 5

    config.core.baud = 921600
    assert config.core.baud == 921600

    config.core.port = "/dev/ttyAMA2"
    assert config.core.port == "/dev/ttyAMA2"

    config.core.tick = 0.5
    assert config.core.tick == 0.5

    config.core.timeout = 10
    assert config.core.timeout == 10

    config.core.handshake_timeout = 12
    assert config.core.handshake_timeout == 12


def test_xbee(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    assert config.xbee.baud == 921600
    assert config.xbee.port == "/dev/ttyAMA0"
    assert config.xbee.api == 2
    assert config.xbee.timeout == 5

    config.xbee.baud = 921600
    assert config.xbee.baud == 921600

    config.xbee.port = "/dev/ttyAMA2"
    assert config.xbee.port == "/dev/ttyAMA2"

    config.xbee.api = 1
    assert config.xbee.api == 1

    config.xbee.timeout = 10
    assert config.xbee.timeout == 10


def test_server(tmp_path: Path):
    config = KevinbotConfig(ConfigLocation.MANUAL, tmp_path.joinpath("config.yaml"))
    assert config.server.root_topic == "kevinbot"

    config.server.root_topic = "test"
    assert config.server.root_topic == "test"
