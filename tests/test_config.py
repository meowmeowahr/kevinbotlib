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


def test_auto_path():
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
