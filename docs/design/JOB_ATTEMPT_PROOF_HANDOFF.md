"The A3 job card is the Rust draft lw-jobcard on anywave/latticeworks branch pl/lw-jobcard-v0 (draft_only, not a frozen contract, PL's JS draft is input only), so CX-029 must not define its own job card and may rely only on the names job_id, attempt_id, worker, slot, epoch, fence, component and result_sha256 as ResultPacket has them, with attempt and proof always carried by reference to job_id, and on nothing about signing bytes, door records or states, which may still change."

# Job, attempt and proof handoff

This pack follows PL-926 and the CX-029 inbox entry at trellis-channel
9c9dd4d2846b127dd345b781547bb41c6a4c0234. The source is draft_only,
has had no hostile review, and PL says it may change. The quoted names are
available; the current ResultPacket definition and per-name producer code were
not found in the searched rpp-spec and trellis-channel repositories.

## Eight names only

| Name | Where the host gets it | Where RPP may carry it |
| --- | --- | --- |
| `job_id` | not found | Native carrier not found; host reference beside MeterRow only. |
| `attempt_id` | not found | Native carrier not found; host reference beside MeterRow only. |
| `worker` | not found | Native carrier not found; host reference beside MeterRow only. |
| `slot` | not found | Native carrier not found; host reference beside MeterRow only. |
| `epoch` | not found | Native carrier not found; host reference beside MeterRow only. |
| `fence` | not found | Native carrier not found; host reference beside MeterRow only. |
| `component` | not found | Native carrier not found; host reference beside MeterRow only. |
| `result_sha256` | not found | Native carrier not found; host reference beside MeterRow only. |

ResultPacket also carries queue, by and sig; these are deliberately not carried.
This is a handoff reference pack, not another job card or a new RPP field.

## MeterRow lookup

A host keeps the existing MeterRow request and row number beside a reference
containing job_id and attempt_id. Two attempts can both contain request 1 and
row 1: they remain distinct through their different attempt_id values under the
same job_id. Local counters alone are not a lookup key across attempts.

Attempt and proof references sit beside job_id, never nested inside a job card.
The result_sha256 name is carried unchanged beside its job_id reference; this
pack adopts no representation or value-domain rule for it or the other names.

## Host duties, not RPP

Host-held identity and persistence stay with the host.

## May change

Nothing beyond the eight quoted names is relied on. In particular:
- Byte conventions of the source draft are not adopted.
- Entry-record details are not adopted.
- Lifecycle vocabulary is not adopted.
- Other draft details remain outside this pack.

## Vector README note

`tests/handoff_vectors.json` contains synthetic examples, not real ResultPacket
exports. Its readme, allowed_names, banned_words, cases, name, valid, meter_rows
and references entries are fixture metadata, not handoff names. The meter_rows
pairs are existing MeterRow request/row context. Only each flat reference uses
the allowed eight-name list. Example values adopt no external types or domains.
Run `python -m unittest tests.test_handoff_vectors` from the repository root.
