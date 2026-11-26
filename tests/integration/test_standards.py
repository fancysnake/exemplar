import os
import subprocess
import tomllib
from pathlib import PurePosixPath

import pytest
from packaging.utils import canonicalize_name

from exemplar.links.standards.filesystem import FilesystemStandardsRepository
from exemplar.pacts import FragmentBit


def test_reads_the_kept_standards(request):
    root = request.config.rootpath / "standards"

    standards = FilesystemStandardsRepository(root).read()

    assert {name: set(category.variants) for name, category in standards.items()} == {
        "ci": {"github"},
        "docs": {"mkdocs-mise", "mkdocs-pyproject"},
        "framework": {"astro", "asyncio", "django", "react"},
        "lang": {"node", "python"},
        "lint": {"oxlint", "ruff"},
        "owner": {"radoslaw-ganczarek"},
        "renovate": {"aube", "hk", "mise-python", "poetry"},
    }


# The check normalises only the repository's requirements, so a constraint or
# a non-normalised spelling in a standard would never match.
def test_pyproject_requirements_are_bare_package_names(request):
    root = request.config.rootpath / "standards"
    standards = FilesystemStandardsRepository(root).read()
    fragments = [
        bit.content
        for category in standards.values()
        for bits in (category.shared, *(v.bits for v in category.variants.values()))
        for bit in bits
        if isinstance(bit, FragmentBit) and bit.path == PurePosixPath("pyproject.toml")
    ]
    requirements = []
    for fragment in fragments:
        project = fragment.get("project", {})
        for group in (
            project.get("dependencies", []),
            *project.get("optional-dependencies", {}).values(),
            *fragment.get("dependency-groups", {}).values(),
        ):
            requirements.extend(item for item in group if isinstance(item, str))

    assert requirements
    assert [r for r in requirements if r != canonicalize_name(r)] == []


# Stands in for `mise where`: prints the install directory the test prepared.
MISE = """#!/bin/sh
echo "$MKDOCS_INSTALL"
"""


@pytest.fixture(name="site_material")
def site_material_fixture(request, tmp_path, monkeypatch):
    stub = tmp_path / "bin" / "mise"
    stub.parent.mkdir()
    stub.write_text(MISE)
    stub.chmod(0o755)
    install = tmp_path / "install"
    packages = install / "mkdocs" / "lib" / "python3.14" / "site-packages"
    (packages / "mkdocs").mkdir(parents=True)
    monkeypatch.setenv("PATH", f"{stub.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("MKDOCS_INSTALL", str(install))
    fragment = (
        request.config.rootpath / "standards/docs/mkdocs-mise/mise.toml/site.toml"
    )
    script = tomllib.loads(fragment.read_text())["tasks"]["site:material"]["run"]

    def site_material(*, material):
        if material:
            (packages / "material").mkdir()
            (packages / "material" / "__init__.py").touch()
        return subprocess.run(
            ["sh", "-c", script], check=False, capture_output=True, text=True
        )

    return site_material


def test_site_material_passes_when_the_mkdocs_install_holds_material(site_material):
    assert site_material(material=True).returncode == 0


def test_site_material_fails_with_the_repair_when_material_is_missing(site_material):
    result = site_material(material=False)

    assert result.returncode == 1
    assert "no mkdocs-material" in result.stderr
    assert "mise install --force pipx:mkdocs" in result.stderr


def test_site_tasks_wait_for_site_material(request):
    fragment = (
        request.config.rootpath / "standards/docs/mkdocs-mise/mise.toml/site.toml"
    )
    tasks = tomllib.loads(fragment.read_text())["tasks"]

    assert tasks["site:build"]["depends"] == ["site:material"]
    assert tasks["site:dev"]["depends"] == ["site:material"]
