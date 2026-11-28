from importlib.metadata import version

import pytest

from exemplar.inits.cli import run


def test_run_prints_installed_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["exemplar", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        run()

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"{version('exemplar')}\n"


def test_check_without_standards_uses_the_shipped_tree(tmp_path, monkeypatch, capsys):
    (tmp_path / "exemplar.toml").write_text("")
    monkeypatch.setattr("sys.argv", ["exemplar", "check", str(tmp_path)])

    with pytest.raises(SystemExit) as exit_info:
        run()

    assert exit_info.value.code == 1
    assert "- [ ] lang: not picked" in capsys.readouterr().out
