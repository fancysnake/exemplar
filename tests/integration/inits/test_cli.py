from importlib.metadata import version

import pytest

from exemplar.inits.cli import run


def test_run_prints_installed_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["exemplar", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        run()

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"{version('exemplar')}\n"
