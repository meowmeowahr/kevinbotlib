# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from pyaudio import PyAudio


class ShutupPyAudio:
    """
    Context manager for PyAudio that redirects all output from C internals to os.devnull.

    Lifted and adapted from StackOverflow Answers:
      https://stackoverflow.com/a/67962563, https://stackoverflow.com/questions/11130156/
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


class DebugPyAudio:
    """
    Context manager for PyAudio that does not block output from C internals.
    """

    def __init__(self):
        self.pyaudio = None

    def __enter__(self) -> PyAudio:
        self.pyaudio = PyAudio()

        return self.pyaudio

    def __exit__(self, *_):
        if self.pyaudio:
            self.pyaudio.terminate()
