# Codex outbox head provenance

New reports identify the final pushed task branch in front matter:

```yaml
branch: codex/<task>
head: refs/heads/codex/<task>
head_kind: final-pushed-branch-ref
source_base: <full source-base commit SHA>
```

`head` names the final remote branch head, rather than its source parent. After
all changes and gates, push normally and resolve that ref with `git ls-remote
origin refs/heads/codex/<task>`. Include the exact returned SHA in the handoff.
The report is itself committed on that branch: embedding that same commit's
literal SHA in its contents would change the SHA. Keep the source base in its
separate field and do not label it as the final head.

Do not edit previously published outboxes to retrofit this convention. Exact
implementation commits may additionally be recorded in a report's status table;
its final remote head is the value resolved from the front-matter ref.
