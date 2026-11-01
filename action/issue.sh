#!/usr/bin/env bash
# Keeps the checklist issue: the one labelled `exemplar`, open while the check
# exits 1 and closed once it exits 0. Reads CHECKLIST, STATUS and GH_REPO.
# Only triagers can label an issue, so nobody else can plant the checklist.
set -euo pipefail

[[ -s "$CHECKLIST" ]] || exit 0
number="$(gh issue list --label exemplar --state all --limit 1 \
  --json number --jq '.[].number')"
if [[ -z "$number" ]]; then
  if [[ "$STATUS" == 1 ]]; then
    gh label create exemplar --force \
      --description "The checklist issue exemplar keeps"
    gh issue create --title "exemplar checklist" --label exemplar \
      --body-file "$CHECKLIST"
  fi
  exit 0
fi
want=open
if [[ "$STATUS" == 0 ]]; then
  want=closed
fi
gh api --method PATCH --silent "repos/$GH_REPO/issues/$number" \
  -F body=@"$CHECKLIST" -f state="$want"
