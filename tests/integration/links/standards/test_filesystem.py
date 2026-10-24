from pathlib import PurePosixPath

import pytest

from exemplar.links.standards.filesystem import FilesystemStandardsRepository
from exemplar.pacts import Category, FileBit, FragmentBit, StandardsError, Variant


def write(path, content=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_reads_categories_variants_and_bits(tmp_path):
    write(tmp_path / "docs/category.toml", "optional = true\n")
    write(tmp_path / "docs/_shared/docs/index.md", "# Home\n")
    write(tmp_path / "docs/mkdocs-mise/mkdocs.yml", "theme: material\n")
    write(tmp_path / "docs/mkdocs-mise/mise.toml/site.toml", "[tasks.site]\n")
    write(tmp_path / "ci/github/.github/workflows/ci.yml", "on: push\n")
    write(tmp_path / "ci/github/.github/workflows/lint.yaml/jobs.yaml", "jobs: {}\n")

    standards = FilesystemStandardsRepository(tmp_path).read()

    assert standards == {
        "ci": Category(
            optional=False,
            shared=(),
            variants={
                "github": Variant(
                    bits=(
                        FileBit(
                            path=PurePosixPath(".github/workflows/ci.yml"),
                            content="on: push\n",
                        ),
                        FragmentBit(
                            path=PurePosixPath(".github/workflows/lint.yaml"),
                            fragment="jobs.yaml",
                            content="jobs: {}\n",
                        ),
                    )
                )
            },
        ),
        "docs": Category(
            optional=True,
            shared=(FileBit(path=PurePosixPath("docs/index.md"), content="# Home\n"),),
            variants={
                "mkdocs-mise": Variant(
                    bits=(
                        FragmentBit(
                            path=PurePosixPath("mise.toml"),
                            fragment="site.toml",
                            content="[tasks.site]\n",
                        ),
                        FileBit(
                            path=PurePosixPath("mkdocs.yml"),
                            content="theme: material\n",
                        ),
                    )
                )
            },
        ),
    }


def test_category_without_category_toml_is_required(tmp_path):
    write(tmp_path / "lint/ruff/ruff.toml")

    standards = FilesystemStandardsRepository(tmp_path).read()

    assert standards["lint"].optional is False


def test_category_toml_without_optional_is_required(tmp_path):
    write(tmp_path / "lint/category.toml")
    write(tmp_path / "lint/ruff/ruff.toml")

    standards = FilesystemStandardsRepository(tmp_path).read()

    assert standards["lint"].optional is False


@pytest.mark.parametrize(
    "category_toml",
    ["optional = 'yes'\n", "required = true\n", "optional = \n"],
    ids=["wrong-type", "unknown-key", "invalid-toml"],
)
def test_bad_category_toml_fails(tmp_path, category_toml):
    write(tmp_path / "lint/category.toml", category_toml)

    with pytest.raises(StandardsError, match=r"category\.toml"):
        FilesystemStandardsRepository(tmp_path).read()


@pytest.mark.parametrize(
    ("stray", "message"),
    [
        ("README.md", "only category directories"),
        ("lint/README.md", "only variant directories"),
        ("lint/ruff/pyproject.toml/tool/ruff.toml", "only fragment files"),
    ],
)
def test_file_out_of_place_fails(tmp_path, stray, message):
    write(tmp_path / "lint/ruff/ruff.toml")
    write(tmp_path / stray)

    with pytest.raises(StandardsError, match=message):
        FilesystemStandardsRepository(tmp_path).read()


def test_missing_root_fails(tmp_path):
    with pytest.raises(StandardsError, match="not a directory"):
        FilesystemStandardsRepository(tmp_path / "standards").read()


def test_non_utf8_bit_fails(tmp_path):
    bit = tmp_path / "lint/ruff/ruff.toml"
    bit.parent.mkdir(parents=True)
    bit.write_bytes(b"\xff")

    with pytest.raises(StandardsError, match="not UTF-8"):
        FilesystemStandardsRepository(tmp_path).read()


def test_broken_symlink_in_variant_fails(tmp_path):
    write(tmp_path / "lint/ruff/ruff.toml")
    (tmp_path / "lint/ruff/gone").symlink_to(tmp_path / "nowhere")

    with pytest.raises(StandardsError, match="only files and directories"):
        FilesystemStandardsRepository(tmp_path).read()


@pytest.mark.parametrize(
    "unreadable",
    ["lint/ruff/ruff.toml", "lint/category.toml", "lint/ruff"],
    ids=["bit", "category-toml", "directory"],
)
def test_unreadable_entry_fails(tmp_path, unreadable):
    write(tmp_path / "lint/category.toml")
    write(tmp_path / "lint/ruff/ruff.toml")
    entry = tmp_path / unreadable
    entry.chmod(0)

    try:
        with pytest.raises(StandardsError, match="Permission denied"):
            FilesystemStandardsRepository(tmp_path).read()
    finally:
        entry.chmod(0o700)


def test_non_utf8_category_toml_fails(tmp_path):
    write(tmp_path / "lint/ruff/ruff.toml")
    (tmp_path / "lint/category.toml").write_bytes(b"\xff")

    with pytest.raises(StandardsError, match="not UTF-8"):
        FilesystemStandardsRepository(tmp_path).read()


def test_category_toml_directory_fails(tmp_path):
    write(tmp_path / "lint/ruff/ruff.toml")
    write(tmp_path / "lint/category.toml/optional.toml")

    with pytest.raises(StandardsError, match="not a file"):
        FilesystemStandardsRepository(tmp_path).read()


def test_none_variant_fails(tmp_path):
    write(tmp_path / "lint/none/ruff.toml")

    with pytest.raises(StandardsError, match="reserved"):
        FilesystemStandardsRepository(tmp_path).read()


@pytest.mark.parametrize(
    "fragment",
    ["mise.toml/site.json", "ci.yml/jobs.toml", "mise.toml/README"],
    ids=["json-in-toml", "toml-in-yml", "no-suffix"],
)
def test_fragment_of_another_format_fails(tmp_path, fragment):
    write(tmp_path / "lint/ruff" / fragment)

    with pytest.raises(StandardsError, match="not the format of"):
        FilesystemStandardsRepository(tmp_path).read()


def test_yml_and_yaml_fragments_mix(tmp_path):
    write(tmp_path / "ci/github/ci.yml/jobs.yaml", "jobs: {}\n")

    standards = FilesystemStandardsRepository(tmp_path).read()

    assert standards["ci"].variants["github"].bits == (
        FragmentBit(
            path=PurePosixPath("ci.yml"), fragment="jobs.yaml", content="jobs: {}\n"
        ),
    )


def test_empty_fragment_directory_fails(tmp_path):
    write(tmp_path / "lint/ruff/ruff.toml")
    (tmp_path / "lint/ruff/pyproject.toml").mkdir()

    with pytest.raises(StandardsError, match="at least one fragment"):
        FilesystemStandardsRepository(tmp_path).read()


@pytest.mark.parametrize(
    "content", ["line\r\nline\r\n", "line\rline\r"], ids=["crlf", "cr"]
)
def test_bit_keeps_line_endings(tmp_path, content):
    bit = tmp_path / "lint/ruff/ruff.toml"
    bit.parent.mkdir(parents=True)
    bit.write_bytes(content.encode())

    standards = FilesystemStandardsRepository(tmp_path).read()

    assert standards["lint"].variants["ruff"].bits == (
        FileBit(path=PurePosixPath("ruff.toml"), content=content),
    )
