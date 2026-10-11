# Licensing

RPP is deliberately dual-licensed:

- **Specification text and documentation** are licensed under the
  [Creative Commons Attribution 4.0 International licence (CC BY 4.0)](LICENSE-CC-BY-4.0).
- **Code** (reference implementations, tools, tests, hardware description sources and build scripts) is licensed
  under the [Apache License, Version 2.0](LICENSE).

The specification is also published as a defensive publication (prior art). No patent claims are made; see
[DEFENSIVE_PUBLICATION.md](DEFENSIVE_PUBLICATION.md) and
[DEFENSIVE_PUBLICATION_2026-10.md](DEFENSIVE_PUBLICATION_2026-10.md).

## Per-path map

| Path | Content | Licence |
|---|---|---|
| `*.md` in the repository root (README, DEFENSIVE_PUBLICATION*, DESIGN_RATIONALE, GOVERNANCE, ...) | specification text and documentation | CC BY 4.0 |
| `spec/` | specification text | CC BY 4.0 |
| `paper/` | paper source (`main.tex`) and its rendered output | CC BY 4.0 |
| `diagrams/` | diagrams (`*.svg`) and their README | CC BY 4.0 (see note 2) |
| `diagrams/interactive-explorer.html` | interactive explorer (markup and script) | Apache-2.0 |
| `landing/`, `docs/` | web pages: the prose is documentation, the markup and script are code | prose CC BY 4.0; markup and script Apache-2.0 |
| `*.png`, `rpp-banner.jsx` in the repository root | banner and launch graphics | CC BY 4.0 |
| `rpp/` | Python reference implementation | Apache-2.0 |
| `rpp_mesh/` | `rpp-mesh` Python package (code); `rpp_mesh/README.md` | Apache-2.0; README CC BY 4.0 |
| `reference/` | Python and Haskell reference implementations | Apache-2.0 |
| `hardware/` | Verilog, Clash/Haskell, simulation and build scripts | Apache-2.0 |
| `hardware/**/*.md` | hardware documentation | CC BY 4.0 |
| `parl/` | code and configuration; `parl/success_criteria.md` | Apache-2.0; the `.md` file CC BY 4.0 |
| `examples/`, `tests/`, `tools/` | example programs, test suites and test vectors, tools | Apache-2.0 |
| `pyproject.toml`, `.zenodo.json`, `.github/` workflows | build, packaging and CI configuration | Apache-2.0 |
| `.github/**/*.md` | issue and PR templates | CC BY 4.0 |

Notes:

1. Where a file states its own licence in its header, that statement applies to that file.
2. `diagrams/README.md` (its "License" section) and Appendix B of `DEFENSIVE_PUBLICATION.md` name **CC BY-SA 4.0**
   for diagrams, while the "Usage" section of `diagrams/README.md`, the README licence table and CONTRIBUTING name
   CC BY 4.0. This map follows the project's stated dual licence (CC BY 4.0); the difference is an open item for
   the author to resolve.
3. Contributions follow the same split: code under Apache-2.0, documentation under CC BY 4.0
   (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Attribution

Please credit: **Alexander Liam Lennon / ANYWAVE**, *Rotational Packet Protocol (RPP)*,
https://github.com/anywave/rpp-spec. See [CITATION.cff](CITATION.cff) and [CONTRIBUTORS.md](CONTRIBUTORS.md).
