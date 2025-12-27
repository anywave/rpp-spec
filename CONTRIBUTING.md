# Contributing to RPP

**Document Version:** 1.0.0
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Welcome

Thank you for your interest in contributing to the Rotational Packet Protocol (RPP) specification. This document provides guidance for contributors, including academic citation requirements and review criteria.

---

## Ways to Contribute

### 1. Report Issues
- Specification ambiguities
- Test vector errors
- Documentation gaps
- Implementation challenges

### 2. Propose Improvements
- Clarifications to existing text
- Additional examples
- New test vectors
- Documentation enhancements

### 3. Implement RPP
- Create implementations in new languages
- Develop integration adapters
- Build developer tools

### 4. Academic Contributions
- Formal verification
- Performance analysis
- Comparative studies
- Extension proposals

---

## Contribution Process

### Step 1: Open an Issue

Before making changes, open an issue to discuss:
- What you want to change
- Why the change is needed
- Potential impact on existing implementations

### Step 2: Fork and Branch

```bash
git clone https://github.com/YOUR_USERNAME/rpp-spec.git
cd rpp-spec
git checkout -b your-feature-branch
```

### Step 3: Make Changes

Follow the style of existing documents:
- Use clear, technical language
- Include examples where helpful
- Update test vectors if changing behavior
- Maintain version numbers

### Step 4: Sign Off (DCO)

All commits must be signed off to certify the Developer Certificate of Origin:

```bash
git commit -s -m "Your commit message"
```

This adds a `Signed-off-by` line certifying you have the right to submit the contribution.

### Step 5: Submit Pull Request

- Reference the related issue
- Describe what changes you made
- Explain why the changes are needed
- Note any backward compatibility implications

---

## Review Criteria

### For Specification Changes (spec/*.md)

Changes to core specification documents are reviewed against:

1. **Necessity:** Is this change required, or nice-to-have?
2. **Clarity:** Does this make the spec clearer?
3. **Consistency:** Does this fit with existing patterns?
4. **Compatibility:** Does this break existing implementations?
5. **Testability:** Can this be verified with test vectors?

**Specification changes require extended review (minimum 2 weeks).**

### For Documentation Changes

- Accuracy
- Clarity
- Completeness
- Consistent formatting

### For Implementation Contributions

- Passes all test vectors
- Follows language idioms
- Includes documentation
- Licensed under Apache 2.0

---

## Backward Compatibility

### Immutable Elements

The following cannot change in minor versions:

- 28-bit address width
- Field positions (Shell, Theta, Phi, Harmonic)
- Bit masks and shifts
- Canonical sector definitions (0-511 ranges)
- Test vectors (results must not change)

### Mutable Elements

The following may be clarified or extended:

- Documentation text
- Additional examples
- New test vectors (that don't contradict existing)
- Implementation guidance

### Breaking Changes

Breaking changes require:
- Major version increment (2.0.0)
- 6-month deprecation period
- Migration guide
- Clear justification

---

## How to Cite RPP in Your Work

### If You Build on RPP

```bibtex
@techreport{rpp2024,
  title     = {Rotational Packet Protocol ({RPP}): A Semantic Addressing
               Architecture for Consent-Aware Memory Systems},
  author    = {{RPP Contributors}},
  year      = {2024},
  version   = {1.0.0},
  url       = {https://github.com/anywave/rpp-spec}
}
```

### If You Extend RPP

For extension proposals, cite the base specification and clearly identify your extensions:

```
This work extends RPP v1.0.0 [1] with [description of extension].

[1] RPP Contributors. (2024). Rotational Packet Protocol (RPP) v1.0.0.
    https://github.com/anywave/rpp-spec
```

### If You Critique RPP

We welcome scholarly critique. Please cite the specific version you analyzed:

```
This analysis examines RPP v1.0.0 [1], specifically the [aspect analyzed].
```

---

## Code of Conduct

### Expected Behavior

- Use clear, professional language
- Provide constructive feedback
- Respect differing viewpoints
- Focus on technical merit

### Unacceptable Behavior

- Personal attacks
- Discrimination
- Spam or off-topic content
- Patent threats

### Enforcement

Violations may result in:
1. Warning
2. Temporary ban (30 days)
3. Permanent ban

Appeals go to the project steward.

---

## Licensing

### Your Contributions

By contributing, you agree that:

1. **Code contributions** are licensed under Apache 2.0
2. **Documentation contributions** are licensed under CC BY 4.0
3. You have the right to make the contribution
4. You understand contributions are public and permanent

### Attribution

Contributors are acknowledged in:
- Git history (permanent)
- CONTRIBUTORS.md (for significant contributions)
- Release notes (for notable changes)

---

## Getting Help

### Questions About the Spec

Open an issue with the `question` label.

### Implementation Help

Open an issue with the `implementation` label.

### Academic Collaboration

Open an issue with the `academic` label or contact maintainers directly.

---

## Recognition

We value all contributions:

| Contribution Type | Recognition |
|-------------------|-------------|
| Bug report | Issue acknowledgment |
| Documentation fix | Git history + thanks |
| Significant feature | CONTRIBUTORS.md entry |
| Academic paper | Links in RELATED_WORK.md |

---

## Frequently Asked Questions

**Q: Can I create a proprietary implementation?**
A: Yes. Apache 2.0 permits proprietary use with attribution.

**Q: Can I extend RPP with proprietary features?**
A: Yes, but proprietary extensions should be clearly identified as non-standard.

**Q: Can I patent my extensions?**
A: We discourage this, but the license permits it for genuinely novel extensions not covered by this specification.

**Q: How long does review take?**
A: Documentation: ~1 week. Specification: ~2-4 weeks. Major changes: ~2 months.

---

*Thank you for contributing to open infrastructure.*
