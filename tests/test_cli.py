# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later


from click.testing import CliRunner

from kevinbotlib.cli import cli


def test_cli_runner():
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0
