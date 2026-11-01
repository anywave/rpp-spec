# Apply RADIX's steward rulings and preserve open baseline review

Document the released migration alternatives, reference Shell-0 software
deadline, experimental device status and software timeout description. Add the
approved overlay text as an informative proposal with the released reuse
direction, distinguish normalized radius values from their encoded byte, and
record all rulings in the governance-required `DECISIONS.md`.

The exact 243 per-ID review annotations remain review-pending; the frozen catalog
stays 243/4/2 open. A future v1→canonical-v2 migration must explicitly name its
radius policy; shell 0–3 examples show neutral byte 128 versus projection bytes
0/85/170/255. No migration API is added. Runtime statements, layouts, header,
constants, vectors and published outboxes remain unchanged; the one package edit
is the authorized timeout docstring.

Validation: 1256 package tests passed; golden 5/0; Ruff 0.14.10 and whitespace
checks exit 0; seven protected software-MUST sentences retained. The registry
has exact LF bytes under a real `autocrlf=true` checkout. Advisory drift exits
**1** with **2 HIGH / 12 MEDIUM / 6 LOW** findings on authorized prose edits,
including frozen format-wording guards; no finding is suppressed or re-baselined.
See `docs/codex/CX006_STEWARD_RULINGS_VALIDATION.md` for every rule/path/line.

Branch: `codex/steward-rulings-2026-10-31` → `master`. The separately authorized
RTL arithmetic repair has its own branch and validation. TR owns PR creation
and merge; this task performs no merge or PR mutation.
