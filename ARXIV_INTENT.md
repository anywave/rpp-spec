# Academic Publication Intent

**Document Version:** 1.0.0
**Last Updated:** 2024-12-27
**Status:** Ready for Submission

---

## Purpose

This document declares the academic intent of the Rotational Packet Protocol (RPP) specification and provides guidance for citation, reproduction, and scholarly use.

---

## Defensive Prior Art Statement

This specification is published as **defensive prior art** under the following principles:

1. **Public Domain Intent:** The RPP addressing architecture is released to establish public domain status for the core technical concepts.

2. **Patent Prevention:** This publication is intended to prevent patent enclosure by any party, including the original authors, by establishing documented prior art with verifiable timestamps.

3. **Open Implementation:** Any party may implement this specification without licensing obligations, subject only to attribution requirements of the applicable licenses (Apache 2.0 for code, CC BY 4.0 for documentation).

4. **Irrevocability:** This prior art declaration is irrevocable. Future versions of this specification may add features but cannot retract the public domain status of concepts published herein.

---

## Publication Targets

### Primary: Zenodo

- **Purpose:** DOI assignment for permanent citation
- **Status:** Ready for submission
- **Expected DOI:** Pending assignment
- **Repository Integration:** GitHub release → Zenodo automatic archival

### Secondary: arXiv

- **Purpose:** Visibility in computer science community
- **Category:** cs.OS (Operating Systems) or cs.DC (Distributed Computing)
- **Status:** Ready for submission pending endorsement
- **Document:** [DEFENSIVE_PUBLICATION.md](DEFENSIVE_PUBLICATION.md)

---

## How to Cite This Work

### Preferred Citation (BibTeX)

```bibtex
@techreport{rpp2024,
  title     = {Rotational Packet Protocol ({RPP}): A Semantic Addressing
               Architecture for Consent-Aware Memory Systems},
  author    = {Lennon, Alexander Liam},
  year      = {2024},
  month     = {December},
  version   = {1.0.0},
  url       = {https://github.com/anywave/rpp-spec},
  note      = {Open specification, Apache 2.0 + CC BY 4.0}
}
```

### Preferred Citation (APA)

```
Lennon, A. L. (2024). Rotational Packet Protocol (RPP): A semantic
addressing architecture for consent-aware memory systems (Version 1.0.0).
https://github.com/anywave/rpp-spec
```

### Preferred Citation (IEEE)

```
A. L. Lennon, "Rotational Packet Protocol (RPP): A Semantic Addressing
Architecture for Consent-Aware Memory Systems," version 1.0.0, Dec. 2024.
[Online]. Available: https://github.com/anywave/rpp-spec
```

### After DOI Assignment

Once a Zenodo DOI is assigned, citations should include:

```bibtex
@techreport{rpp2024,
  title     = {Rotational Packet Protocol ({RPP}): A Semantic Addressing
               Architecture for Consent-Aware Memory Systems},
  author    = {Lennon, Alexander Liam},
  year      = {2024},
  month     = {December},
  version   = {1.0.0},
  doi       = {10.5281/zenodo.XXXXXXX},
  url       = {https://github.com/anywave/rpp-spec}
}
```

---

## Versioning for Academic Use

### Specification Versions

| Version | Status | Citability |
|---------|--------|------------|
| 1.0.0 | Stable | Citable as canonical reference |
| 1.x.x | Minor updates | Citable; note specific version |
| 2.x.x | Major revision | Cite as separate work |

### Citing Specific Versions

For reproducibility, cite the specific version used:

```
Lennon, A. L. (2024). Rotational Packet Protocol (RPP) (Version 1.0.0).
```

Git tags and GitHub releases provide permanent references to specific versions.

---

## Academic Use Policy

### Permitted Uses

- **Research:** Use RPP concepts in academic research without restriction
- **Publication:** Publish analyses, extensions, or critiques with attribution
- **Teaching:** Use specification in educational contexts with attribution
- **Implementation:** Create conforming implementations under Apache 2.0

### Attribution Requirements

1. **For Specification Use:** Cite using formats above
2. **For Code Derivation:** Include Apache 2.0 license notice
3. **For Documentation Derivation:** Include CC BY 4.0 attribution

### No Restrictions On

- Commercial use of implementations
- Modification and redistribution
- Creation of derivative works
- Competitive implementations

---

## Reproducibility

### Reference Implementation

The canonical Python implementation ([reference/python/rpp_address.py](reference/python/rpp_address.py)) serves as the authoritative reference for resolving ambiguities in the specification text.

### Test Vectors

Official test vectors ([tests/test_vectors.json](tests/test_vectors.json)) enable independent verification of implementation correctness.

### Version Control

All specification history is preserved in Git. Any statement about RPP can be verified against the historical record.

---

## Contact for Academic Inquiries

For questions regarding:
- Citation format
- Academic collaboration
- Endorsement for arXiv submission
- Clarification of specification intent

Open an issue on GitHub: https://github.com/anywave/rpp-spec/issues

---

## Timestamps and Verification

### Publication Timeline

| Date | Event |
|------|-------|
| 2024-12-27 | Initial GitHub publication |
| 2024-12-27 | Version 1.0.0 release tagged |
| Pending | Zenodo DOI assignment |
| Pending | arXiv submission |

### Verification

Publication timestamps can be independently verified via:
- Git commit history
- GitHub release timestamps
- Zenodo archival timestamp (after DOI assignment)
- arXiv submission timestamp (after acceptance)

---

## Prior Art Scope

This publication establishes prior art for:

1. **28-bit semantic addressing format** with Shell/Theta/Phi/Harmonic fields
2. **Spherical coordinate addressing** for functional classification
3. **Consent-aware address resolution** as intrinsic property
4. **Bridge architecture** for semantic routing to existing storage
5. **Sector-based functional classification** (Gene, Memory, Witness, Dream, etc.)
6. **Grounding-level encoding** (physical → abstract spectrum)

This list is illustrative, not exhaustive. The complete prior art scope encompasses all concepts described in the specification documents.

---

*This document is part of the RPP specification and is released under CC BY 4.0.*
