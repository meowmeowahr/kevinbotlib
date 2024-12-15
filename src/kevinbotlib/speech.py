# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import subprocess
from abc import ABC, abstractmethod
from multiprocessing import Process as _Process
from os import PathLike

from command_queue import CommandQueue as _CommandQueue
from command_queue.commands import BaseCommand as _BaseCommand
from loguru import logger

from pyaudio import PyAudio, paInt16

# https://stackoverflow.com/a/67962563
class _shutup_pyaudio:
    """
    PyAudio is noisy af every time you initialise it, which makes reading the
    log output rather difficult.  The output appears to be being made by the
    C internals, so I can't even redirect the logs with Python's logging
    facility. Therefore, the nuclear option was selected: swallow all stderr
    and stdout for the duration of PyAudio's use.

    Lifted and adapted from StackOverflow:
      https://stackoverflow.com/questions/11130156/
    """

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for _ in range(2)]

        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

        self.pyaudio = None

    def __enter__(self) -> PyAudio:
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

        self.pyaudio = PyAudio()

        return self.pyaudio

    def __exit__(self, *_):
        if self.pyaudio:
            self.pyaudio.terminate()

        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)

        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)

class _debug_pyaudio:
    """
    Context manager for PyAudio
    """

    def __init__(self):
        self.pyaudio = None

    def __enter__(self) -> PyAudio:
        self.pyaudio = PyAudio()

        return self.pyaudio

    def __exit__(self, *_):
        if self.pyaudio:
            self.pyaudio.terminate()

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

        # Attempt to retrive the bitrate
        try:
            with open(self._model + ".json") as config:
                bitrate = int(json.loads(config.read())["audio"]["sample_rate"])
        except (KeyError, json.JSONDecodeError, FileNotFoundError):
            bitrate = 22050
            logger.warning("Bitrate config data parsing failure. Assuming bitrate for `medium` quality (22050)")

        with (_shutup_pyaudio() if not self.debug else _debug_pyaudio()) as audio:
            stream = audio.open(
                format=paInt16,
                channels=1,
                rate=bitrate,
                output=True
            )

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
            with subprocess.Popen(piper_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL if not self.debug else None) as piper_process:
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
