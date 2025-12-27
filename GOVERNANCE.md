# RPP Governance

**Version:** 1.0.0
**Last Updated:** 2024-12-27

---

## 1. Philosophy

RPP governance is designed to be:
- **Minimal**: Only enough process to prevent chaos
- **Transparent**: All decisions documented publicly
- **Stable**: Spec changes are rare and deliberate
- **Forkable**: If governance fails, the spec survives

---

## 2. Roles

### 2.1 Steward

The **Steward** (initially the project founder) is responsible for:
- Final decisions on spec changes
- Maintaining canonical documentation
- Resolving disputes
- Approving major releases

The Steward is a role, not an owner. The project is not property.

### 2.2 Contributors

**Contributors** are anyone who:
- Submits code, documentation, or feedback
- Reports issues or bugs
- Reviews pull requests
- Participates in discussions

All contributions are valued equally regardless of size.

### 2.3 Maintainers

**Maintainers** are trusted contributors who can:
- Merge pull requests
- Triage issues
- Manage releases

Maintainers are appointed by the Steward based on consistent, quality contributions.

---

## 3. Decision Making

### 3.1 Types of Decisions

| Decision Type | Process | Who Decides |
|---------------|---------|-------------|
| Bug fixes | PR + review | Maintainers |
| Minor clarifications | PR + review | Maintainers |
| Spec additions | RFC + discussion | Steward |
| Spec changes | RFC + extended review | Steward + community |
| Governance changes | RFC + consensus | Steward + maintainers |

### 3.2 RFC Process

For significant changes:

1. **Propose**: Open an issue with `[RFC]` prefix
2. **Discuss**: Minimum 2 weeks for community feedback
3. **Revise**: Address feedback and concerns
4. **Decide**: Steward makes final call with rationale
5. **Document**: Decision recorded in DECISIONS.md

### 3.3 Conflict Resolution

1. **Discussion**: Attempt to resolve through dialogue
2. **Mediation**: Uninvolved maintainer mediates
3. **Steward Decision**: Steward makes binding decision
4. **Documentation**: Reasoning publicly documented

---

## 4. Contribution Guidelines

### 4.1 Code Contributions

- All code must pass existing tests
- New code must include tests
- Code style should match existing patterns
- Reference implementations must be parity-tested

### 4.2 Documentation Contributions

- Follow existing document structure
- Include version and date
- Cross-reference related documents
- Use clear, technical language

### 4.3 Developer Certificate of Origin

By contributing, you certify that:

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

Sign-off commits with: `Signed-off-by: Your Name <email@example.com>`

---

## 5. Versioning

### 5.1 Spec Versioning

RPP follows semantic versioning for the specification:

- **Major (X.0.0)**: Breaking changes to addressing format
- **Minor (0.X.0)**: New optional features, clarifications
- **Patch (0.0.X)**: Typos, editorial fixes

### 5.2 Compatibility Promises

| Version Change | Compatibility |
|----------------|---------------|
| Patch | Fully compatible |
| Minor | Backward compatible |
| Major | May break implementations |

**Major version changes require:**
- 6-month advance notice
- Migration guide
- Extended support for previous version

---

## 6. Forking Philosophy

Forks are **healthy** and **welcomed**.

If you disagree with project direction:
1. Fork freely under Apache 2.0
2. Maintain attribution per license
3. Consider a different name to avoid confusion

The spec is designed to survive governance failure.

---

## 7. Code of Conduct

### 7.1 Core Values

- **Respect**: Treat all participants with dignity
- **Clarity**: Communicate clearly and honestly
- **Patience**: Help newcomers learn
- **Focus**: Stay on technical topics

### 7.2 Unacceptable Behavior

- Personal attacks or harassment
- Discrimination of any kind
- Deliberate misinformation
- Spam or off-topic content

### 7.3 Enforcement

1. **Warning**: First offense, private warning
2. **Temporary Ban**: Second offense, 30-day ban
3. **Permanent Ban**: Third offense, permanent removal

Appeals go to the Steward.

---

## 8. Intellectual Property

### 8.1 No Patents

This project explicitly rejects patent protection.

- No contributor may patent RPP-related innovations
- Contributions imply patent grant per Apache 2.0
- Patent assertions trigger automatic license termination

### 8.2 Trademark

The name "RPP" and "Rotational Packet Protocol" are not trademarked.
Use them freely with accurate attribution.

---

## 9. Contact

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Security**: security@[project-domain]

---

## 10. Amendments

This governance document may be amended through the RFC process.

All changes require:
- Public proposal
- 2-week comment period
- Steward approval
- Updated version number

---

*Governance inspired by: Apache Foundation, Linux Foundation, Rust Project*
