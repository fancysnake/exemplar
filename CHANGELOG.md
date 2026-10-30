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
- A category, variant, root or key in `exemplar.toml` holding a non-printable
  character, such as a line break, is refused as a problem and never printed,
  so it cannot forge a ticked checklist item.
- Documentation site at <https://exemplar.fancysnake.dev>, built by
  `mise run site:build`.

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
