import os
import subprocess

import pytest

# Logs each call's arguments and answers `issue list` with GH_ISSUE
GH = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$GH_LOG"
if [[ "$1 $2" == "issue list" && -n "${GH_ISSUE:-}" ]]; then
  echo "$GH_ISSUE"
fi
"""
LIST = "issue list --label exemplar --state all --limit 1 --json number --jq .[].number"
LABEL = "label create exemplar --force --description The checklist issue exemplar keeps"
CREATE = "issue create --title exemplar checklist --label exemplar --body-file {}"
PATCH = "api --method PATCH --silent repos/owner/repo/issues/7 -F body=@{} -f state="


@pytest.fixture(name="keep")
def keep_fixture(request, tmp_path, monkeypatch):
    stub = tmp_path / "bin" / "gh"
    stub.parent.mkdir()
    stub.write_text(GH)
    stub.chmod(0o755)
    log = tmp_path / "gh.log"
    log.touch()
    monkeypatch.setenv("PATH", f"{stub.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_LOG", str(log))
    monkeypatch.setenv("GH_REPO", "owner/repo")
    monkeypatch.setenv("CHECKLIST", str(tmp_path / "checklist.md"))
    script = request.config.rootpath / "action" / "issue.sh"

    def keep(status, issue, checklist="- [ ] package.json\n"):
        (tmp_path / "checklist.md").write_text(checklist)
        monkeypatch.setenv("STATUS", status)
        monkeypatch.setenv("GH_ISSUE", issue)
        subprocess.run(["bash", script], check=True)
        return log.read_text().splitlines()

    return keep


@pytest.mark.parametrize(
    ("status", "issue", "calls"),
    [
        pytest.param("1", "", [LIST, LABEL, CREATE], id="creates"),
        pytest.param("0", "", [LIST], id="creates-nothing-ticked"),
        pytest.param("0", "7", [LIST, PATCH + "closed"], id="closes"),
        pytest.param("1", "7", [LIST, PATCH + "open"], id="opens"),
    ],
)
def test_keeps_the_checklist_issue(keep, tmp_path, status, issue, calls):
    checklist = tmp_path / "checklist.md"

    assert keep(status, issue) == [call.format(checklist) for call in calls]


def test_leaves_the_issue_without_a_checklist(keep):
    assert not keep("1", "7", checklist="")
