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
- Documentation site at <https://exemplar.fancysnake.dev>, built by
  `mise run site:build`.

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
