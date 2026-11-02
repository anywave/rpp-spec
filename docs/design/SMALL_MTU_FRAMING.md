# Small-MTU control framing (CX-021)

This local, experimental transport carries the existing 112-byte control envelope.
It changes no RPP address, header, signature, permission or policy rule. It adds
no cryptography. A complete datagram becomes a control frame only through
`rpp_control::decode`, using the caller's verifier and expected recipient. The
host still checks membership, consent and replay before effects.

## Prior art and reuse decision

Read-only source review on 2026-11-02: RFC Editor requests returned HTTP 403 under
the configured proxy. RFC statements below are qualified background descriptions,
not a claim that their normative text was retrieved. Upstream Zephyr and Semtech
source files linked below were retrieved and inspected. No board was contacted.

| Mechanism | Existing facility | Fit and decision |
| --- | --- | --- |
| [BLE L2CAP LE credit-based channels](https://www.bluetooth.com/specifications/specs/core-specification-5-4/) | SDUs are segmented into credit-controlled PDUs. [Zephyr L2CAP](https://github.com/zephyrproject-rtos/zephyr/blob/main/subsys/bluetooth/host/l2cap.c) has segmented dynamic-channel send handling. | Use the underlay's segmentation; skip `rpp-frag`. |
| [GATT prepare/execute long writes](https://www.bluetooth.com/specifications/specs/core-specification-5-4/) | Prepared writes have offsets and an execute/cancel procedure; they are not notifications. [Zephyr ATT definitions](https://github.com/zephyrproject-rtos/zephyr/blob/main/subsys/bluetooth/host/att_internal.h) declare prepare, execute, notify and default LE MTU 23. | Use long writes when the chosen adapter supports them; skip `rpp-frag`. For default-MTU notifications, use the local framing below. |
| [RFC 4944 section 5.3 FRAG1/FRAGN](https://www.rfc-editor.org/rfc/rfc4944.html#section-5.3) | Four-byte first and five-byte subsequent headers encode an 11-bit size, 16-bit tag and subsequent offset in eight-byte units. Normative page unavailable here. | Reuse the subsequent-header shape with explicitly different local semantics below. No 6LoWPAN interoperability claim. |
| [RFC 8724 SCHC No-ACK](https://www.rfc-editor.org/rfc/rfc8724.html) | Profile-defined fragmentation with RuleID, DTag, window/fragment fields and final integrity handling; No-ACK does not request receiver acknowledgments. Normative page unavailable here. | Reuse a deployed SCHC adaptation where available; selecting a profile or implementing its integrity mechanism is outside this control-only helper. |
| [LoRaWAN L2 specification](https://resources.lora-alliance.org/technical-specifications) | The MAC does not provide general datagram segmentation. Regional payload limits depend on data rate and configuration. [Semtech EU868 table](https://github.com/Lora-net/LoRaMac-node/blob/master/src/mac/region/RegionEU868.h) lists 51 bytes at DR0. | Use local framing only if no deployed underlay fragmentation exists. The 51-byte fixture assumes that application budget, without extra FOpts overhead. |

These are source-derived fixture budgets: BLE ATT_MTU 23 minus one opcode and
two handle bytes gives 20; the cited EU868 DR0 table gives 51. Neither is a
measurement, a universal negotiated MTU, or a promise of radio delivery.

## Local derivative and imposed choices

Every fragment has five bytes: `11100sss size-low tag-high tag-low offset`.
Size is the 11-bit big-endian RFC 4944 field; tag is big-endian 16-bit. Offset
is a byte offset. Payload follows immediately and must be nonempty.

- **IMPOSED:** use the FRAGN-shaped five-byte header even at offset zero, and
  interpret offsets as bytes. This permits every MTU of at least six and avoids
  padding/alignment machinery for small control frames. This is a private local
  derivative, not an IPv6/6LoWPAN packet or a standard wire extension.
- **IMPOSED:** cap this derivative at 255 bytes, even if a larger const generic
  is requested. The one-byte offset stays sufficient; the default cap is 112.
- **IMPOSED:** refuse a new datagram when all slots are live. Never evict one in
  progress. Different total sizes for a live peer/tag are rejected.
- **IMPOSED:** use caller-provided opaque 16-byte peer/link identifiers, tags and
  monotonic logical ticks. They associate fragments, not authenticate them.
  The adapter must bind the peer identifier to its actual ingress context.

Fragments can arrive out of order. Preflight bounds and every conflicting byte
before writing. Identical duplicate bytes change neither coverage, the remembered tick nor
the original deadline. Completion requires all bytes, then decoding clears the slot
on success or failure. No unchecked completed-byte API exists. Decoding does not
provide host replay protection; tag reuse and sequence policy remain host duties.
A verified completion retains its peer/tag until the original deadline in a
FIFO cache of exactly two keys. A retained late key returns `RecentlyCompleted`
without opening a slot or invoking the verifier; duplicates do not extend its
lifetime or reorder FIFO. Failed verification never populates this cache. A third
verified completion evicts the oldest key; this is bounded suppression only.

Deadlines are half-open: `tick >= start + timeout` is expired. Checked deadline
addition rejects overflow. A matching expired key is cleared and returns
`Expired`. Empty slots take priority. Reclaiming an unrelated expired slot first
returns `ExpiredKey { peer, tag }` naming the old key, without consuming incoming
bytes. Handle that event, then retry the identical fragment locally once; the
freed empty slot makes this bounded. No expiry queue can overflow or lose events.
Rejected clock rollback changes nothing; malformed input cannot clear a slot or
advance its clock. Other rejected fragments do not change coverage.
No wall clock, allocation, thread, network, retry, acknowledgment or integrity
algorithm is introduced. Authentication remains the complete envelope verifier.

An ESP32 adapter still needs a named board/stack, negotiated-MTU/characteristic
configuration, authenticated ingress binding, bounded queues, tag allocation,
tick source, caller verifier, host consent/replay checks and hardware tests.
