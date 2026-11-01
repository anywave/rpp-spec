# Scripted overlay scenarios

All measurements, prior verification outcomes and times are fixtures.
No network or cryptographic operation occurs.

| Tick | Request | Class | Path | Status | Tokens | Detail |
|---:|---:|---|---|---|---:|---|
| 0 | 1 | data | lan | OK | 3 | direct |
| 0 | 2 | control | bt | OK | 0 | ALIVE |
| 0 | 3 | control | lora | OK | 0 | ROUTE-AROUND |
| 1 | 4 | data | wifi | OK | 3 | direct |
| 2 | 5 | data | a-r/r-b | OK | 3 | relay |
| 3 | 6 | data | lan | FAILED | 0 | retry-before-first-token |
| 3 | 6 | data | internet | OK | 3 | direct |
| 4 | 7 | data | lan | FAILED | 1 | terminal-after-first-token |
| 5 | 8 | data | internet | OK | 3 | direct |
| 6 | 9 | data | lan | OK | 3 | direct |
| 7 | 10 | data |  | NO_CHANNEL | 0 |  |
| 7 | 11 | data |  | DENIED | 0 |  |
| 8 | 12 | billboard | lan | DELIVERED | 0 | rule-1 |
| 8 | 13 | billboard | lan | HELD_UNTIL_SINCE | 0 | fact-1 |
| 8 | 14 | billboard |  | DENIED | 0 |  |
| 8 | 15 | control |  | DENIED | 0 |  |
| 10 | 16 | billboard |  | DENIED | 0 |  |

Billboards are inert structured statements. Application policy would interpret authorized facts/rules;
the simulator only reports the active set, never executes a rule or supplies model instructions.

| Tick | Active receipts |
|---:|---|
| 8 | rule-1 |
| 9 | fact-1, rule-1 |
| 10 | fact-1 |
| 11 | (none) |
