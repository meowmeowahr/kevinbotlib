# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import subprocess
from abc import ABC, abstractmethod
from multiprocessing import Process as _Process
from os import PathLike
from pathlib import Path

import platformdirs
from command_queue.commands import BaseCommand as _BaseCommand
from loguru import logger
from pyaudio import paInt16

from kevinbotlib.audioutils import DebugPyAudio, ShutupPyAudio
from kevinbotlib.config import KevinbotConfig


def _abslistdir(directory):
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))


def get_user_piper_model_dir():
    return os.path.join(platformdirs.user_data_dir("kevinbotlib", "meowmeowahr"), "piper")


def get_system_piper_model_dir():
    return os.path.join(platformdirs.site_config_dir("kevinbotlib", "meowmeowahr"), "piper")


def get_models_paths(user: bool = True, system: bool = True):
    if user and system:
        return list(filter(lambda x: x.endswith(".onnx"), _abslistdir(get_user_piper_model_dir()))) + list(filter(lambda x: x.endswith(".onnx"), _abslistdir(get_system_piper_model_dir())))
    elif user:
        return list(filter(lambda x: x.endswith(".onnx"), _abslistdir(get_user_piper_model_dir())))
    elif system:
        return list(filter(lambda x: x.endswith(".onnx"), _abslistdir(get_system_piper_model_dir())))
    else:
        raise ValueError("At least one of user or system must be True")


def get_models(user: bool = True, system: bool = True) -> dict[str, str]:
    """Get the name and directory of all installed models

    Returns:
        dict[str, str]: Name and directory pair
    """

    models = {}
    for model_path in get_models_paths(user, system):
        models[Path(model_path).name.split(".")[0]] = model_path
    return models


class BaseTTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str):
        """Abstract speak method.

        Args:
            text (str): text to synthesize
        """

    def speak_in_background(self, text: str):
        p = _Process(target=self.speak, args=(text,))
        p.start()


class PiperTTSEngine(BaseTTSEngine):
    """
    Text to Speech Engine using rhasspy/Piper.
    You will need to provide your own executable for this to work.
    """

    def __init__(self, model: str, executable: PathLike | str | None = None) -> None:
        """Constructor for PiperTTSEngine

        Args:
            executable (PathLike | str | None): Piper executable location. If None, uses executable defined in config
            model (str): Pre-downloaded Piper model
        """
        super().__init__()

        if executable is None:
            conf = KevinbotConfig()
            executable = conf.piper_tts.executable
            
        self.executable = executable
        self._model: str = model
        self._debug = False

    @property
    def model(self):
        """Getter for the currently loaded model.

        Returns:
            str: model name
        """
        return self._model

    @model.setter
    def model(self, value: str):
        """Setter for the currently loaded model.

        Args:
            value (str): model name
        """
        self._model = value

    @property
    def debug(self) -> bool:
        """Getter for debug mode state.

        Returns:
            bool: whether debug mode is enabled
        """
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        """Setter for debug mode.
        Enables ALSA output from PyAudio and stderr output from Piper

        Args:
            value (bool): whether debug mode is enabled
        """
        self._debug = value

    def speak(self, text: str):
        """Synthesize the given text using the set piper executable. Play it in real-time over the system's speakers.

        Args:
            text (str): Text to synthesize
        """

        modelfile = get_models()[self._model]

        # Attempt to retrive the bitrate
        try:
            with open(modelfile + ".json") as config:
                bitrate = int(json.loads(config.read())["audio"]["sample_rate"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            bitrate = 22050
            logger.warning("Bitrate config data parsing failure. Assuming bitrate for `medium` quality (22050)")

        with ShutupPyAudio() if not self.debug else DebugPyAudio() as audio:
            stream = audio.open(format=paInt16, channels=1, rate=bitrate, output=True)

            # Set up Piper synthesis command
            piper_command = [
                self.executable,
                "--model",
                modelfile,
                "--config",
                modelfile + ".json",
                "--output-raw",
            ]

            # Use subprocess to pipe synthesis to playback
            with subprocess.Popen(
                piper_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL if not self.debug else None,
            ) as piper_process:
                if piper_process.stdin and piper_process.stdout:
                    piper_process.stdin.write(text.encode("utf-8"))
                    piper_process.stdin.close()

                    while True:
                        data = piper_process.stdout.read(1024)
                        if not data:
                            break
                        stream.write(data)

                piper_process.wait()

            stream.stop_stream()
            stream.close()


class ManagedSpeaker:
    """
    Manage speech so that only one string is played. Playing a new string will cancel the previous one.
    """

    def __init__(self, engine: BaseTTSEngine) -> None:
        self.engine = engine
        self.process: _Process | None = None

    def speak(self, text: str):
        """
        Stop any current speech and start a new one.

        Args:
            text (str): Text to synthesize
        """
        self.cancel()
        self.process = _Process(target=self.engine.speak, args=(text,), daemon=True)
        self.process.start()

    def cancel(self):
        """Attempt to cancel the current speech."""
        if self.process and self.process.is_alive():
            self.process.terminate()


class SpeechCommand(_BaseCommand):
    """
    Command queue command for speech. Will hold up to queue during speech processing.
    """

    def __init__(self, engine: BaseTTSEngine, text: str):
        """
        Constructor for SpeechCommand

        Args:
            engine (BaseTTSEngine): Text to Speech engine to use
            text (str): Text to synthesize
        """
        super().__init__()
        self.text = text
        self.engine = engine
        self.command = self.execute

    def execute(self):
        self.engine.speak(self.text)


class MultiprocessingSpeechCommand(SpeechCommand):
    """
    Speech command for command queue that synthesizes speech in a background process.
    """

    def launch(self):
        _Process(target=self._command, daemon=True).start()
