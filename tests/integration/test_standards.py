from pathlib import PurePosixPath

from packaging.utils import canonicalize_name

from exemplar.links.standards.filesystem import FilesystemStandardsRepository
from exemplar.pacts import FragmentBit


def test_reads_the_kept_standards(request):
    root = request.config.rootpath / "standards"

    standards = FilesystemStandardsRepository(root).read()

    assert {name: set(category.variants) for name, category in standards.items()} == {
        "ci": {"github"},
        "docs": {"mkdocs-mise", "mkdocs-pyproject"},
        "framework": {"astro", "django", "react"},
        "lang": {"node", "python"},
        "lint": {"ruff"},
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
