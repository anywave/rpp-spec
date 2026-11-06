# HEDERA-DAY1-FIX: HCS fee protocol and SDK boundary evidence

**The zero-custom-fee policy is supported:** a nonempty `max_custom_fees` list containing the transaction payer and exactly one zero-HBAR `FixedFee` prevents both positive HBAR custom fees and every HTS denomination omitted from the list. A mirror preflight is an additional refusal check; the serialized consensus limit closes a fee-schedule change between preflight and consensus.

**Current RADIX scope is testnet-only alpha:** day-1 code must have no mainnet client, mirror or enable-flag path. Every concrete send/resend re-reads the runtime network selection and refuses non-testnet or changed configuration. The fee protocol below is unchanged by this narrower scope.

Research used public source reads and credential-free offline protobuf construction. No key material, operator account, network submission, mainnet request or live smoke was used. The earlier author verification did not cover custom fees or all asynchronous send boundaries; the independent R-HEDERA-DAY1 review identified those gaps.

## Authoritative consensus behavior

The consensus source is pinned to **hiero-consensus-node `9efa5c465a49249e55235d560b4c8addad4a0182`** (the GitHub main head observed and independently matched by a shallow public-source clone).

1. **Empty outer list means unbounded custom fees.** [TransactionBody field documentation, lines 777–784](https://github.com/hiero-ledger/hiero-consensus-node/blob/9efa5c465a49249e55235d560b4c8addad4a0182/hapi/hedera-protobuf-java-api/src/main/proto/services/transaction.proto#L777) states the optional list's empty meaning. [ConsensusSubmitMessageHandler lines 150–158](https://github.com/hiero-ledger/hiero-consensus-node/blob/9efa5c465a49249e55235d560b4c8addad4a0182/hedera-node/hedera-consensus-service-impl/src/main/java/com/hedera/node/app/service/consensus/impl/handlers/ConsensusSubmitMessageHandler.java#L150) skips `validateFeeLimits` when the outer list is empty, then assesses applicable fees.
2. **Zero is a valid maximum allowance.** [PreCheckValidator `checkMaxCustomFees`, lines 64–90](https://github.com/hiero-ledger/hiero-consensus-node/blob/9efa5c465a49249e55235d560b4c8addad4a0182/hedera-node/hedera-app-spi/src/main/java/com/hedera/node/app/spi/validation/PreCheckValidator.java#L64) requires each payer's fees list to be nonempty and rejects only negative amounts. It also validates payer/denomination IDs. Thus `fees:[]` is invalid, but `fees:[{amount:0}]` with the denomination omitted is valid. The [primary test helper at lines 172–174](https://github.com/hiero-ledger/hiero-consensus-node/blob/9efa5c465a49249e55235d560b4c8addad4a0182/hedera-node/hedera-app-spi/src/test/java/com/hedera/node/app/spi/validation/PreCheckValidatorTest.java#L172) includes a zero amount in a valid limit. Do not confuse this with the separate topic-schedule validator, which requires a configured fee itself to be positive.
3. **Unlisted HTS denominations are denied, not unbounded.** [Handler `validateFeeLimits`, lines 387–417](https://github.com/hiero-ledger/hiero-consensus-node/blob/9efa5c465a49249e55235d560b4c8addad4a0182/hedera-node/hedera-consensus-service-impl/src/main/java/com/hedera/node/app/service/consensus/impl/handlers/ConsensusSubmitMessageHandler.java#L387) selects limits for the actual payer. For each charged token denomination it requires a matching limit; no match produces **`NO_VALID_MAX_CUSTOM_FEE`**. A matched amount below the charged total produces **`MAX_CUSTOM_FEE_LIMIT_EXCEEDED`**. For positive aggregate HBAR it requires an HBAR limit and compares against it; zero therefore rejects any positive aggregate HBAR.
4. **Limits apply only to supported transaction types.** The same generic validator rejects a nonempty limits list on unsupported functionality with `MAX_CUSTOM_FEES_IS_NOT_SUPPORTED`. Apply the custom-fee limit to **message submit**, not topic creation. Preserve the separate network transaction-fee ceiling on both.

Fees can be exempted when the payer is the collector, a relevant token treasury, or satisfies a topic's fee-exempt key. The handler filters these before validating/charging; an exemption charges no such fee. The stricter proposed preflight nevertheless rejects every configured fee entry, even an exempt or zero entry. This keeps eligibility independent of exemption behavior and malformed amounts.

This is source-level consensus evidence. The Java node test suite was not executed here and no deployed testnet version was queried. Live testnet proof remains a separate required result.

## Exact pinned SDK APIs

All limits must be set **before freezing/signing** and serialized into every per-node transaction alternative. In protobuf terms the invariant is `max_custom_fees.length == 1`, payer equals transaction payer, `fees.length == 1`, amount equals zero, and `denominating_token_id` is absent. The inner zero amount may use protobuf's default scalar encoding; the repeated `FixedFee` message entry must remain present.

**JavaScript `@hiero-ledger/sdk 2.90.1`:**

```js
transaction.setCustomFeeLimits([
  new CustomFeeLimit({
    accountId: payer,
    fees: [new CustomFixedFee({amount: 0})],
  }),
]);
```

The [versioned CustomFeeLimit implementation](https://github.com/hiero-ledger/hiero-sdk-js/blob/v2.90.1/src/transaction/CustomFeeLimit.js) emits `accountId` plus the inner fixed-fee messages. `TopicMessageSubmitTransaction.setCustomFeeLimits` is available in this version. An independent credential-free probe froze an actual SDK submit transaction, decoded `TransactionList` → `SignedTransaction` → `TransactionBody`, and confirmed the invariant. Result: one variant, one payer limit, one zero fee, token absent. No signer or operator was constructed.

**Rust `hiero-sdk 0.45.0`:**

```rust
transaction.custom_fee_limits([CustomFeeLimit::new(
    Some(payer),
    vec![CustomFixedFee {
        amount: 0,
        denominating_token_id: None,
        fee_collector_account_id: None,
    }],
)]);
```

The public fields/constructor are in [custom_fee_limit.rs](https://github.com/hiero-ledger/hiero-sdk-rust/blob/v0.45.0/src/custom_fee_limit.rs); `custom_fee_limits` and `get_custom_fee_limits` are in [transaction/mod.rs](https://github.com/hiero-ledger/hiero-sdk-rust/blob/v0.45.0/src/transaction/mod.rs). The builder accepts any iterator of `CustomFeeLimit`. The implementation converts each entry to protobuf `FixedFee`, preserving amount zero and an absent denomination. The alpha implementation additionally pins one public testnet node and checks the single serialized node alternative; its final validation is separate from this research.

**Python community Pre-Alpha `hiero-sdk-python 0.3.0`:**

```python
transaction.set_custom_fee_limits([
    sdk.CustomFeeLimit(
        payer_id=payer,
        custom_fees=[sdk.CustomFixedFee(amount=0, denominating_token_id=None)],
    ),
])
```

The pinned wheel includes `CustomFeeLimit`, `CustomFixedFee` and `TopicMessageSubmitTransaction.set_custom_fee_limits`; no protobuf patch or replacement SDK is needed. See [release CustomFeeLimit](https://github.com/hiero-ledger/hiero-sdk-python/blob/v0.3.0/src/hiero_sdk_python/transaction/custom_fee_limit.py) and [release submit builder](https://github.com/hiero-ledger/hiero-sdk-python/blob/v0.3.0/src/hiero_sdk_python/consensus/topic_message_submit_transaction.py). An independent published-wheel probe round-tripped the resulting `TransactionBody` protobuf and confirmed one limit, one inner zero-HBAR fee and absent denomination. This is not live network confirmation or official Python SDK support.

## Mirror preflight schema

Mirror source is pinned to **hiero-mirror-node `87884a06cba0ff8bafbddf247ab9565f39739211`**. [OpenAPI `ConsensusCustomFees`, lines 3583–3592](https://github.com/hiero-ledger/hiero-mirror-node/blob/87884a06cba0ff8bafbddf247ab9565f39739211/rest/api/v1/openapi.yml#L3583) is an **object**, not an array:

```json
{"custom_fees":{"created_timestamp":"1234567890.000000001","fixed_fees":[]}}
```

`created_timestamp` is optional in the schema; when present it references `Timestamp`, a string, rather than `TimestampNullable`. `fixed_fees` contains `FixedCustomFee` objects. The [Topic schema, line 4362](https://github.com/hiero-ledger/hiero-mirror-node/blob/87884a06cba0ff8bafbddf247ab9565f39739211/rest/api/v1/openapi.yml#L4362) uses this object. Requiring the expected topic ID, a readable object, an actual empty `fixed_fees` array and no unknown fee fields is a conservative eligibility policy. Refuse missing/null/malformed schedules and every nonempty schedule, including positive HBAR, token-denominated, zero, exempt and malformed entries. Do not treat absent information as a no-fee schedule. This refusal happens before signing/preparation and the consensus allowance still protects against a later schedule change.

## Concrete asynchronous send boundary (F2 note)

In JS SDK 2.90.1, topic transaction `_execute(channel,request)` delegates to the channel, but that is **not the last asynchronous boundary**. [NodeChannel](https://github.com/hiero-ledger/hiero-sdk-js/blob/v2.90.1/src/channel/NodeChannel.js) awaits `_initializeClient()`, then `waitForReady`, then invokes gRPC `makeUnaryRequest`. It also initializes gRPC with `grpc.enable_retries:1`. Therefore a runtime-network check only before signing, before `tx.execute`, or in transaction `_execute` leaves an in-flight configuration-change gap.

The JS owner was notified to re-read `HEDERA_NETWORK` immediately before the concrete synchronous gRPC `makeUnaryRequest` invocation and refuse any non-testnet or changed selection, disable transparent gRPC retries, keep SDK attempts at one, and let the shared layer own its bounded retry budget. Tests should change the network selection during delayed SDK preparation, delayed channel initialization, delayed readiness and outer retry delay. Mainnet support and the previous enable flag must be removed rather than retained behind this check. A narrow pinned-SDK channel customization must document its private-API dependency and fail closed if the hook changes. No such transport implementation was authored by this research agent.

Public raw source downloads returned HTTP 200 through the existing permitted proxy path. Local evidence is in `/workspace/work/hedera-fix-protocol/`, including pinned source/proto/schema files and precheck/handler tests. The shallow public source clone is `/workspace/work/hedera-fix-node-src/`; it contains no product repository changes or credentials.

Rust 0.45.0 exposes an additional dispatch constraint: `TransactionData`/`TransactionExecute` and the execution plumbing are re-exported only `pub(crate)` in the published crate's `src/transaction/mod.rs`. Its `src/execute.rs` performs asynchronous node selection/pings before the private `execute_single` invokes the transport. A client `max_attempts(1)` is an outer retry limit; a layer can still visit multiple configured node alternatives for a retryable precheck. Pinning a prepared transaction to one node bounds this internal fan-out. No supported public channel/interceptor hook was found during this source inspection. Claiming a runtime check immediately at the Rust RPC dispatch requires a demonstrated integration hook, a reviewed SDK change, or a separate dispatcher over the already-frozen official-SDK bytes; a check immediately before `tx.execute().await` is not evidence of that narrower guarantee. With the current testnet-only client and no mainnet route, a changed environment cannot redirect the frozen write to mainnet. The remaining distinction concerns refusal/timing semantics and attempt accounting, and should be stated accurately rather than hidden by a fake-only test.
