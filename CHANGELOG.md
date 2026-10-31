# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

### Added

- `exemplar` command line, printing its version.
- `exemplar check`: checks a repository against the standards tree and prints
  a markdown checklist of every bit under each root; exits 1 while any item is
  open.
- YAML is read by the YAML 1.2 core schema, as the tools it configures read it:
  `on` and `12:30` stay strings and `0755` is decimal. Merge keys (`<<`) still
  merge.
- An `exemplar.toml` whose category, variant, root or unknown key holds a
  non-printable character, such as a line break, is refused whole, like
  malformed TOML, and the name is never printed, so it cannot forge a ticked
  checklist item.
- Documentation site at <https://exemplar.fancysnake.dev>, built by
  `mise run site:build`.
- `lang` standard: `python` and `node` variants, holding the `pyproject.toml`,
  `mise.toml` and `package.json` settings every maintained repository shares.
- GitHub Action `fancysnake/exemplar@main`: runs `exemplar check` on the
  checked-out repository against the standards it ships with, writes the
  checklist to the job summary and fails while any item is open.

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
