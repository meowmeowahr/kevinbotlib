# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


class HandshakeTimeoutException(BaseException):
    """Exception that is produced when the connection handshake times out"""


class JoystickMissingException(BaseException):
    """Exception that is produced when a requested gamepad is missing"""


class CommandSchedulerAlreadyExistsException(BaseException):
    """Exception that is produced when an attempt to create more than one command scheduler was made"""
