# HEDERA-DAY1 SDK/public-source check

Observed in this session, 2026-11-06 UTC (2026-11-05 America/Los_Angeles). These are live registry/source checks, not copied version claims from the October/November internal notes. No credentials, signing, accounts, or ledger writes were used for this research.

## SDKs to ship

| Language | Current published package to pin | Status and runtime | License evidence |
| --- | --- | --- | --- |
| JavaScript / TypeScript | `@hiero-ledger/sdk` **2.90.1** | Official native SDK; JavaScript package includes TypeScript declarations (`lib/index.d.ts`); Node >=18 according to package. [Live npm metadata](https://registry.npmjs.org/@hiero-ledger%2fsdk/latest), [version manifest](https://github.com/hiero-ledger/hiero-sdk-js/blob/v2.90.1/package.json). | **Apache-2.0** from registry/manifest and [version LICENSE](https://github.com/hiero-ledger/hiero-sdk-js/blob/v2.90.1/LICENSE). |
| Rust | `hiero-sdk` **0.45.0** (`use hiero_sdk` or dependency alias chosen locally) | Official Hiero Rust SDK; latest published, non-yanked crates.io version, uploaded 2026-04-30. Upstream `main` currently says **0.46.0**, which is not the published version. [Live crates.io metadata](https://crates.io/api/v1/crates/hiero-sdk), [version Cargo.toml](https://github.com/hiero-ledger/hiero-sdk-rust/blob/v0.45.0/Cargo.toml). Upstream requirements include Rust, protoc, OpenSSL. | **Apache-2.0** from registry/manifest and [version LICENSE](https://github.com/hiero-ledger/hiero-sdk-rust/blob/v0.45.0/LICENSE). |
| Python | `hiero-sdk-python` **0.3.0**, import `hiero_sdk_python` | **Community-maintained Hiero project, Pre-Alpha**, not one of Hedera's six officially supported language SDKs. Published 2026-10-11; PyPI 0.3.0 requires Python >=3.10,<4. Upstream `main` now requires >=3.11,<4, so use release metadata for the pin. [Live PyPI metadata](https://pypi.org/pypi/hiero-sdk-python/json), [release manifest](https://github.com/hiero-ledger/hiero-sdk-python/blob/v0.3.0/pyproject.toml). If "official SDK only" is strict, Python must call a reviewed JS/Rust boundary instead; there is no official-supported pure-Python package to name. | **Apache-2.0** from PyPI classifier/license and [release LICENSE](https://github.com/hiero-ledger/hiero-sdk-python/blob/v0.3.0/LICENSE). |

[Hedera's official SDK catalog](https://docs.hedera.com/native/fundamentals) explicitly names six official languages: JavaScript, Java, Go, Swift, Rust, C++; it places Python in community language SDKs. The [native landing page](https://docs.hedera.com/native) also labels Python community-maintained. The [Hiero catalog](https://docs.hiero.org/sdks) marks Rust/JavaScript maintainer Hiero and Python maintainer Community. Do not describe Python 0.3.0 as official or production-stable. Its official repository status does not change its support classification. No GA claim was established for any 0.x Rust/Python version.

The official native landing page still suggests `cargo add hedera`. The registry and released Cargo manifest establish the renamed published Rust package `hiero-sdk=0.45.0`; use the latter for new integration.

Legacy namespaces found in existing research/code:

- `@hashgraph/sdk` latest registry version is **2.81.0**, Apache-2.0, pointing at the same Hiero JS repo. The modern `@hiero-ledger/sdk` has advanced to 2.90.1. [Legacy npm metadata](https://registry.npmjs.org/@hashgraph%2fsdk/latest).
- `hedera` crate latest is **0.43.0**, Apache-2.0, uploaded 2026-01-08. It points at the Hiero Rust repository, but is behind renamed `hiero-sdk`. [Legacy crates metadata](https://crates.io/api/v1/crates/hedera).
- `hedera-sdk-py` latest is **2.50.0**, Python>=3.8, Apache classifier/[license](https://github.com/wensheng/hedera-sdk-py/blob/master/LICENSE), owned by [wensheng/hedera-sdk-py](https://github.com/wensheng/hedera-sdk-py). It is the older community Java SDK bridge, **not** the Hiero pure-Python project or an official Hedera SDK. [Legacy PyPI metadata](https://pypi.org/pypi/hedera-sdk-py/json).

## Agent Kit / MCP and the first Digigami tool

Live npm and upstream manifests agree with SCOUT-r0: `@hashgraph/hedera-agent-kit` **4.2.0**, `@hashgraph/hedera-agent-kit-mcp` **1.2.0**, both **Apache-2.0** and both require Node `^22.23.4 || ^24.22.1 || >=26.12.1`. Their ledger peer is `@hiero-ledger/sdk ^2.90.1`. This is stricter than the ledger SDK's Node>=18. [Core npm](https://registry.npmjs.org/@hashgraph%2fhedera-agent-kit/latest), [MCP npm](https://registry.npmjs.org/@hashgraph%2fhedera-agent-kit-mcp/latest), [core source manifest](https://github.com/hashgraph/hedera-agent-kit-js/blob/main/packages/core/package.json), [MCP source manifest](https://github.com/hashgraph/hedera-agent-kit-js/blob/main/packages/mcp/package.json), [repository LICENSE](https://github.com/hashgraph/hedera-agent-kit-js/blob/main/LICENSE).

Preserve the scout's order **A (read-only synthetic statement inspector), then B (testnet HCS digest preparer), then C (unsigned payout preview)**. TR-1800i asks for a bounded audit reader and unsigned testnet payout preview; TR-1802i authorizes iterative private builds with RADIX approval of exact public repo/content/license before publication. The new HEDERA-DAY1 request independently authorizes runtime-environment-signed testnet smoke proof; it does not authorize adding operator keys to the read-only MCP or making autonomous public tools. The shared smoke layer need not import Agent Kit or an LLM framework. Keep Node tooling separate from Rust desktop builds.

The hosted Network MCP is separate from docs search and local MCP Toolkit; its wallet signing/OAuth behavior is described in the existing scout but was not re-executed in this research. No unsupported claim of hosted wallet interoperability, caps, tool execution, or promotion readiness is made. No social/email messages or public publication occurred.

## Reachability and evidence

The execution network policy is enforced restricted HTTP, `vpn_configured:false`, and TCP grants are empty. The runtime has no configured secrets/runtime variables/outbound identities. Ordinary sandbox commands initially failed to create sockets (`Operation not permitted`); using supported per-command `with_additional_permissions` with `network.enabled:true` allowed existing proxy access to the permitted registries and GitHub hosts without changing proxy settings.

- **Reached HTTP 200:** npm modern/legacy SDK, npm Agent Kit/MCP, crates.io `hiero-sdk`/`hedera`, PyPI modern/legacy SDK, raw GitHub main/release manifests and licenses, Rust GitHub tag listing. Evidence is in `/workspace/work/hedera-sdk-evidence/` with metadata SHA-256, URLs, byte counts, and response status.
- **Direct executor docs access blocked:** `https://docs.hedera.com/hedera/sdks-and-apis/sdks` returned proxy CONNECT **403 Forbidden** because docs.hedera.com is not in the allowed hosts. Do not bypass that denial.
- **Docs successfully reached through the available web search connector:** `https://docs.hedera.com/native`, `https://docs.hedera.com/native/fundamentals`, `https://docs.hiero.org/sdks`. These provided the official/community classification above. The older docs URL redirects to `native/fundamentals` in the connector.
- **HTTP 404:** guessed `hiero-sdk-python/main/docs/overview.md` and `hedera-docs/main/native/fundamentals.mdx`; they are not evidence. The real raw `hashgraph/hedera-docs/main/native/index.mdx` returned 200 and corroborated Python's community classification and JS install command.
- **Not evaluated by this research:** testnet consensus/mirror reachability, funded disposable testnet credential availability, HTS/NFT/scheduled transaction execution, and transitive dependency license/security audit. Package licenses are first-party licenses; resolved dependency notice inventory is separate distribution work.

Evidence manifests: `metadata.json`, `metadata-extra.json`, `metadata-pinned.json`; compact combined source metadata is `sources.json`. Raw source bytes contain only public package/source data; no runtime keys or environment values were fetched or written.
