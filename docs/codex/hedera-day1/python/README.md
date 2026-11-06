# Python shared policy and experimental transport

`rpp.adapters.hedera_safe` is the shared Python HCS policy layer. `HederaTransport`
keeps its default in-memory mode; its real publishing path now fails closed and
uses this layer instead of returning an empty object from an unwritten stub.
The historical theta-to-topic mapping remains; it cannot allocate new topic IDs.

Hedera's official SDK list excludes Python. `hiero-sdk-python==0.3.0` is hosted by
Hiero, Apache-2.0, community maintained, and classified Pre-Alpha by PyPI. It is
**experimental, not a shipping official SDK replacement**. Alpha Python callers
should use the official JavaScript/Rust write boundary. The optional
`hedera-experimental` dependency and `HEDERA_EXPERIMENTAL_PYTHON_ENABLED=true` runtime
flag permit explicit experiments with this transport. Nothing loads `.env` files.

Sources checked: https://docs.hedera.com/native/fundamentals,
https://docs.hiero.org/sdks, https://pypi.org/pypi/hiero-sdk-python/json,
https://github.com/hiero-ledger/hiero-sdk-python.

Runtime configuration: `HEDERA_NETWORK` defaults to testnet; mainnet requires
`RADIX_HEDERA_MAINNET_ENABLED` equal to literal `true`. Only RADIX controls that
deployment flag; possession of this environment variable does not authenticate a
person. No flag was enabled here. The smoke always refuses mainnet regardless.
`HEDERA_OPERATOR_ID` and `HEDERA_OPERATOR_KEY` are read only at client creation.
Config objects, representations, returned receipts and errors contain no keys.
Credential constructor arguments are rejected, including in mock mode.

`HEDERA_MAX_FEE_TINYBARS` defaults to and cannot exceed 100000000 (1 test HBAR per
transaction); SDK queries use the same maximum. `HEDERA_MAX_ATTEMPTS` defaults to
3, capped at 5. `HEDERA_MIRROR_ATTEMPTS` defaults to 20, capped at 30;
`HEDERA_RETRY_DELAY_MS` defaults to 1000, capped at 5000. SDK calls time out after
10 seconds; TLS verification stays on. Frozen signed transaction identity is
retained across SDK retries. Application code never reconstructs an uncertain
write. Reconcile its transaction ID before a manual rerun.

Topic creation requires a SUCCESS receipt, matching mirror metadata and submit
key, and matching successful creation transaction with operator payer identity.
Submission checks SUCCESS plus mirror topic, operator payer, receipt sequence and
base64-decoded bytes. Payloads larger than 1024 bytes are refused, avoiding
multi-chunk writes with incomplete receipt verification. Redirects are refused.
The smoke signs an envelope, verifies its signature locally, submits it, and
checks exact mirror bytes. It creates no accounts or tokens and uses no real HBAR.

Run from the repo: `python -m pytest -q tests/test_hedera_safe.py`,
`python scripts/hedera_python_mutations.py`, and
`python scripts/hedera_python_smoke.py`. Live proof requires a throwaway testnet
operator supplied through runtime environment and allowed Hedera consensus/mirror
egress, plus `HEDERA_TESTNET_THROWAWAY=true` runtime attestation. This environment
has neither; a BLOCKED smoke is not a testnet pass.

For legacy `silver-pancake/hedera`, replace automatic success-on-stub fallback with
this explicit policy or the official write boundary. Keep AVT, Vizor and Soul NFT
writes closed until HTS/NFT receipt and mirror contracts have equivalent tests.
No changes to that historical checkout are claimed by this branch.
