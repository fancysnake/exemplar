from typer.testing import CliRunner

from exemplar.gates.cli.typer import CliGate

# click's exit code for a usage error, which a bare `exemplar` is
USAGE_ERROR = 2


def test_version_prints_and_exits():
    result = CliRunner().invoke(CliGate(version="1.2.3").app, ["--version"])

    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_no_arguments_prints_help():
    result = CliRunner().invoke(CliGate(version="1.2.3").app, [])

    assert result.exit_code == USAGE_ERROR
    assert "Usage: " in result.output
