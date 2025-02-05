# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


class HandshakeTimeoutException(BaseException):
    """Exception that is produced when the connection handshake times out"""
