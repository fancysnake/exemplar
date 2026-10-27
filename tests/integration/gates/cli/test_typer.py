import pytest
from typer.testing import CliRunner

from exemplar.gates.cli.typer import CliGate
from exemplar.inits.cli import audit

# click's exit code for a usage error, which a bare `exemplar` is
USAGE_ERROR = 2

STANDARDS = {
    "lint/_shared/LICENSE": "MIT\n",
    "lint/ruff/ruff.toml": "line-length = 88\n",
    "lint/ruff/pyproject.toml/ruff.toml": "[tool.ruff]\nline-length = 88\n",
    "lang/node/.nvmrc": "24\n",
}
PICKS = 'lint = "ruff"\n\n[lang.node]\nroot = ["frontend", "admin"]\n'
PASSING = {
    "exemplar.toml": PICKS,
    "LICENSE": "MIT\n",
    "ruff.toml": "line-length = 88\n",
    "pyproject.toml": "[project]\nname = 'x'\n\n[tool.ruff]\nline-length = 88\n",
    "frontend/.nvmrc": "24\n",
    "admin/.nvmrc": "24\n",
}


def write(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


@pytest.fixture(name="standards")
def standards_fixture(tmp_path):
    return write(tmp_path / "standards", STANDARDS)


def check(repo, standards):
    gate = CliGate(version="1.2.3", audit=audit)
    return CliRunner().invoke(
        gate.app, ["check", str(repo), "--standards", str(standards)]
    )


def test_version_prints_and_exits():
    result = CliRunner().invoke(
        CliGate(version="1.2.3", audit=audit).app, ["--version"]
    )

    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_no_arguments_prints_help():
    result = CliRunner().invoke(CliGate(version="1.2.3", audit=audit).app, [])

    assert result.exit_code == USAGE_ERROR
    assert "Usage: " in result.output


def test_passing_repo_ticks_every_bit_by_root(tmp_path, standards):
    result = check(write(tmp_path / "repo", PASSING), standards)

    assert result.exit_code == 0
    assert result.output == (
        "### lint: ruff\n"
        "\n"
        "- [x] pyproject.toml ⊇ ruff.toml\n"
        "- [x] ruff.toml\n"
        "- [x] LICENSE\n"
        "\n"
        "### lang: node (frontend)\n"
        "\n"
        "- [x] .nvmrc\n"
        "\n"
        "### lang: node (admin)\n"
        "\n"
        "- [x] .nvmrc\n"
    )


def test_failing_bits_are_open_with_their_problem(tmp_path, standards):
    repo = write(
        tmp_path / "repo",
        PASSING | {
            "ruff.toml": "line-length = 100\n",
            "pyproject.toml": "[tool.ruff]\nline-length = 100\n",
        },
    )
    (repo / "admin/.nvmrc").unlink()

    result = check(repo, standards)

    assert result.exit_code == 1
    assert result.output == (
        "### lint: ruff\n"
        "\n"
        "- [ ] pyproject.toml ⊇ ruff.toml — tool.ruff.line-length: expected 88,"
        " got 100\n"
        "- [ ] ruff.toml — differs from the standard\n"
        "- [x] LICENSE\n"
        "\n"
        "### lang: node (frontend)\n"
        "\n"
        "- [x] .nvmrc\n"
        "\n"
        "### lang: node (admin)\n"
        "\n"
        "- [ ] .nvmrc — missing\n"
    )


def test_pick_problems_are_open_under_exemplar_toml(tmp_path, standards):
    repo = write(
        tmp_path / "repo",
        PASSING | {
            "exemplar.toml": 'lint = "ruff"\ndocs = "x"\n\n[lang.node]\nroot = "/"\n'
        },
    )

    result = check(repo, standards)

    assert result.exit_code == 1
    assert result.output == (
        "### exemplar.toml\n"
        "\n"
        "- [ ] docs: unknown category\n"
        "- [ ] lang.node: root `/` is not inside the repository\n"
        "\n"
        "### lint: ruff\n"
        "\n"
        "- [x] pyproject.toml ⊇ ruff.toml\n"
        "- [x] ruff.toml\n"
        "- [x] LICENSE\n"
    )


def test_missing_exemplar_toml_is_open(tmp_path, standards):
    result = check(write(tmp_path / "repo", {"LICENSE": "MIT\n"}), standards)

    assert result.exit_code == 1
    assert result.output == "### exemplar.toml\n\n- [ ] missing\n"


def test_broken_standards_is_a_usage_error(tmp_path, standards):
    (standards / "stray.txt").write_text("")

    result = check(write(tmp_path / "repo", PASSING), standards)

    assert result.exit_code == USAGE_ERROR
    assert "Invalid value for '--standards'" in result.output
    assert "stray.txt: the standards root holds only category directories" in (
        result.output
    )


def test_repo_must_be_a_directory(tmp_path, standards):
    result = check(tmp_path / "nowhere", standards)

    assert result.exit_code == USAGE_ERROR
    assert "does not exist" in result.output
