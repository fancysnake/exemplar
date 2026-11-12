# Adopting exemplar

A repository adopts exemplar in one pull request. The workflow runs on that
pull request, so the checklist shows what is left before the merge.

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

Add the files of your `ci` variant as [Standards § ci](standards.md#ci) shows
them.

## 3. Open the pull request

The `exemplar` job prints the checklist in its summary and fails while any
item is open. Each open item names the file and what is wrong with it. Fix the
files, push, and repeat until the job passes.

## 4. Merge

From now on the workflow runs on every pull request, on every push to `main` or
`master`, and every Monday; [Checking a repository](checking.md#in-ci) says
when it opens the checklist issue.
