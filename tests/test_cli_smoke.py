from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_help_succeeds() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_serve_help_succeeds() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    # Check for port option (may contain ANSI codes in CI)
    assert "port" in result.output.lower()
