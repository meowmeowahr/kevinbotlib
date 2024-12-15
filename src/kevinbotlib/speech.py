# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import platform
import subprocess
from abc import ABC, abstractmethod
from multiprocessing import Process as _Process
from os import PathLike

from command_queue import CommandQueue as _CommandQueue
from command_queue.commands import BaseCommand as _BaseCommand
from loguru import logger


class BaseTTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str):
        pass

    def speak_in_background(self, text: str):
        p = _Process(target=self.speak, args=(text,))
        p.start()


class PiperTTSEngine(BaseTTSEngine):
    def __init__(self, executable: PathLike | str | None, model: str) -> None:
        super().__init__()

        if executable is None:
            executable = "piper"
        self.executable = executable
        self._model: str = model
        self._debug = False

    @property
    def model(self):
        """Getter for the current loaded model.

        Returns:
            str: model name
        """
        return self._model

    @model.setter
    def model(self, value: str):
        """Setter for the current loaded model.

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

        Args:
            value (bool): whether debug mode is enabled
        """
        self._debug = value

    def speak(self, text: str):
        """Synthesize the given text using the set piper executable. Play it in real-time over the system's speakers.

        Args:
            text (str): Text to synthesize
        """

        # Attempt to retrive the bitrate
        try:
            with open(self._model + ".json") as config:
                bitrate = int(json.loads(config.read())["audio"]["sample_rate"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            bitrate = 22050
            logger.warning("Bitrate config data parsing failure. Assuming bitrate for `medium` quality (22050)")

        if platform.system() == "Linux":
            playback_command = ["aplay", "-r", str(bitrate), "-f", "S16_LE", "-t", "raw"]
        else:
            msg = "Unsupported platform for streaming playback. Currently, only Linux is supported"
            raise OSError(msg)

        # Set up Piper synthesis command
        piper_command = [
            self.executable,
            "--model",
            self._model,
            "--config",
            self._model + ".json",
            "--output-raw",
        ]

        # Use subprocess to pipe synthesis to playback
        with (
            subprocess.Popen(
                piper_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL if not self.debug else None,
            ) as piper_process,
            subprocess.Popen(
                playback_command, stdin=piper_process.stdout, stderr=subprocess.DEVNULL if not self.debug else None
            ),
        ):
            if piper_process.stdin:  # will always be true
                piper_process.stdin.write(text.encode("utf-8"))
                piper_process.stdin.close()
            piper_process.wait()


class SpeechCommand(_BaseCommand):
    def __init__(self, engine: BaseTTSEngine, text: str):
        self.text = text
        self.engine = engine
        self.command = self.execute

    def execute(self):
        self.engine.speak(self.text)


class MultiprocessingSpeechCommand(SpeechCommand):
    def launch(self):
        _Process(target=self._command, daemon=True).start()


class SpeechQueue(_CommandQueue):
    pass
