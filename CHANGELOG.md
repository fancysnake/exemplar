# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

### Added

- `exemplar` command line, printing its version.
- Documentation site at <https://exemplar.fancysnake.dev>, built by
  `mise run site:build`.
- Bits are checked against the repository: whole files byte for byte,
  fragments as a deep subset of the TOML, YAML or JSON file they name.

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html
