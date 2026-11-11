# Adopting exemplar

A repository adopts exemplar in one pull request that adds three files. The
workflow runs on that pull request, so the checklist shows what is left before
the merge.

## 1. Pick the variants

Write `exemplar.toml` at the repository root, with one line per category.
[Standards](standards.md) lists the categories and the variants of each.

```toml
ci = "github"
lang = "python"
```

A variant that lives in a subdirectory takes a table with a `root`;
[Standards](standards.md) shows the form.

## 2. Add the workflow

Copy this file to `.github/workflows/exemplar.yml` unchanged. It is a bit of
the `ci` standard, so an edited copy fails the check.

```yaml
--8<-- "standards/ci/github/.github/workflows/exemplar.yml"
```

## 3. Keep Renovate off the workflow

Merge this rule into `renovate.json`, or create the file with it. The check
asks for the rule even in a repository that does not run Renovate.

```json
--8<-- "standards/ci/github/renovate.json/exemplar.json"
```

## 4. Open the pull request

The `exemplar` job prints the checklist in its summary and fails while any
item is open. Each open item names the file and what is wrong with it. Fix the
files, push, and repeat until the job passes.

## 5. Merge

From now on the workflow runs on every pull request, on every push to `main` or
`master`, and every Monday. When the standards here change, the next run
fails, and the next push to the default branch opens an issue labelled
`exemplar` in the repository, with the checklist in it. The issue closes itself
once every item is ticked.
[Checking a repository](checking.md#in-ci) has the details.
