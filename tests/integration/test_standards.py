from exemplar.links.standards.filesystem import FilesystemStandardsRepository


def test_reads_the_kept_standards(request):
    root = request.config.rootpath / "standards"

    standards = FilesystemStandardsRepository(root).read()

    assert {name: set(category.variants) for name, category in standards.items()} == {
        "lang": {"node", "python"}
    }
