# Security Policy

## Reporting a vulnerability

Please report security problems privately through GitHub's private vulnerability reporting:

**https://github.com/anywave/rpp-spec/security/advisories/new**

Do not open a public issue, pull request or discussion for a suspected vulnerability.

Please include:

- what is affected (specification section, Python package `rpp-protocol` or `rpp-mesh` and its version, Haskell
  reference, or hardware source);
- how to reproduce it, and what you expected instead;
- the impact as you understand it.

We will acknowledge the report, keep you informed while we look at it, and credit you in the advisory unless you
ask us not to.

## Scope and limits

RPP is a research specification with reference implementations. The reference code has not had an independent
security audit, and nothing in this repository should be read as a security guarantee. In particular, an RPP
address carries a consent level, but a consent level stated in a packet is a claim: an enforcement point must
check it against consent state it holds itself.

## Supported versions

Security fixes are made on the `master` branch and in the latest release of each Python package on PyPI.
