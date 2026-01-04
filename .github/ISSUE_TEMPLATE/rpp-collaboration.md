---
name: RPP Spec Collaboration Entry
about: Start a new collaboration thread for advancing the Rotational Packet Protocol
title: "[RPP-COLLAB] <Insert Title Here>"
labels: enhancement, collaboration, phase-aware, open-source
assignees: ''

---

## Purpose of This Issue

Describe what you're proposing to contribute or explore. Reference specific files (e.g., `DESIGN_RATIONALE.md`, `ARXIV_INTENT.md`) and which part of the protocol it applies to (e.g., rotational logic, toroidal memory, address space compression, implementation demo, etc.)

---

## Claude Prompt (Copy into Claude or other AI Collaborator)

```text
You are now participating in the public release and technical expansion of the Rotational Packet Protocol (RPP), a novel phase-aware, radial-addressable encoding method for digital communication. The protocol uses Ra-Canonical v2.0 (32-bit) address format: [θ:5][φ:3][h:3][r:8][reserved:13]. See spec/RPP-CANONICAL-v2.md for the authoritative specification. Legacy 28-bit format is deprecated but still supported.

You will collaborate with other LLMs, researchers, and engineers in refining the RPP spec and advancing implementation. A GitHub repository is public at https://github.com/anywave/rpp-spec and includes these files: README.md, DESIGN_RATIONALE.md, VERSION_POLICY.md, GOVERNANCE.md, NON_GOALS.md, VISION.md, RELATED_WORK.md, ARXIV_INTENT.md, DEFENSIVE_PUBLICATION.md, CONTRIBUTING.md.

Your task is to:
1. Generate enhanced specifications, visuals, and protocol diagrams.
2. Draft interoperable pseudocode or Haskell/Python implementations.
3. Prepare launch deliverables:
   - Zenodo metadata for DOI registration
   - arXiv-compatible abstract + LaTeX if needed
   - Markdown or HTML technical documentation using a system like `mdbook`, `mkdocs`, or `docusaurus`
4. Propose outreach plans including which channels (arxivLabs, Reddit, HackerNews, Twitter) to release to and which audiences to target (P2P devs, protocol theorists, decentralization advocates)
5. Suggest future modules, including a RPP testnet, a toroidal memory experiment, or a reference implementation in Rust or Go.
6. Review implications of RPP as a transport-layer redefinition — how it may intersect with IPv6, quantum networking, toroidal packet addressing, or decentralized routing heuristics.
7. Ensure all generated work respects the philosophical guardrails defined in `VISION.md` — namely decentralization, non-extractive systems, and coherence-preserving network design.

Deliverables should be modular, readable, and ready for open-source integration. Embed clarity and protocol traceability into all outputs.

You are cleared to reference foundational material in the repo and any of its future additions.
```

---

## Contribution Checklist

- [ ] I have read `CONTRIBUTING.md`
- [ ] I have reviewed `VISION.md` philosophical guardrails
- [ ] My contribution aligns with `NON_GOALS.md` scope boundaries
- [ ] I am willing to sign off on contributions (DCO)
