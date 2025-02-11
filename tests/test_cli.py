from click.testing import CliRunner

from kevinbotlib.cli import cli


def test_cli_runner():
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0
