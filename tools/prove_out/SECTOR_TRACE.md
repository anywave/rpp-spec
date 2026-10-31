# CX-004 Part C — read-only sector trace notes

Source: anywave/rpp-spec `0a12c8dc311e27816a99b69c1cb2f1e7d9cb282e`, branch `codex/coherence-sector-prove-out` in `/workspace/cx004-prove-out`. Latest TR inbox was read at `/tmp/cx001-trellis-inbox` FETCH_HEAD `d9214588220854667692ad5614d355763360133d` before work. No project files, code, constants, tests, spec or vectors were changed by this trace.

## What sector denotes

There are at least four related but distinct uses. None is a physical unit or content measurement.

| Definition | Input and computation | Domain/range/units | Consequence | Source |
|---|---|---|---|---|
| Legacy v1 semantic class | decoded theta; ranges [0,63]...[448,511], equivalently theta//64 with named tuple | valid theta integer0..511, eight labels; dimensionless | CLI display, consent sensitivity, resolver path category | rpp/address.py:25-41,96-114,135-184; rpp/consent.py:52-103 |
| Canonical v2 symbolic class | Repitan theta lookup with ranges1–3,4–6,7–10,11–13,14–17,18–20,21–24,25–27 | valid theta1..27; eight different names CORE,GENE,MEMORY,WITNESS,DREAM,BRIDGE,GUARDIAN,SHADOW; dimensionless | .sector, same_sector, named adjacency, address constructor | rpp/address_canonical.py:83-145,350-353,498-513,557-580 |
| RoutableSector admission enum | caller explicitly requests enum VOID0,CORE1,...SHADOW8; consent lookup; coherence only gives VOID zero exception | nine enum values, coherence integer0..674, five-state header consent | direct admission/denial or redirect to GUARDIAN; not a geometric partition of raw addresses by itself | rpp/sector_router.py:24-120,128-158,278-348 |
| Network coverage zone | theta//64 of HOT node coordinates | eight zone indices0..7 covering valid theta0..511 | fewer than3 Hot neighbors per zone is a gap; local gradient routing still operates on angular coordinates | rpp/network.py:41-42,94-103,280-324,387-408 |

The legacy classes are Gene,Memory,Witness,Dream,Bridge,Guardian,Emergence,Meta. Each is exactly64 theta codes. Every valid28-bit address falls into exactly one, because `(address >> 17) & 0x1FF` is in0..511 and integer division by64 yields one of0..7. The remaining19 bits do not enter this classifier: each sector contains64*4*512*256 =33,554,432 valid raw addresses; the eight classes cover268,435,456. Exhaustively exercising512 theta equivalence classes is complete for this classifier; it is not a brute-force enumeration of268 million addresses.

The canonical domain is1..27, partition sizes3,3,4,3,4,3,4,3. Raw encodings0,28..31 are handled as INVERSE/META sentinels (`address_canonical.py:100-109`), not valid Repitan classes; `RPPAddress.__post_init__` accepts bit-range representations and `is_valid()` distinguishes valid1..27. Do not claim all32 represent the same eight ordinary sectors.

## Documentation and labels

- `spec/SEMANTICS.md:99` calls theta functional classification. Its table123-130 explicitly agrees with the v1 code and SVG. Its fixed-meaning promise311-315 concerns the v1 map: Gene0..63 stays identity. It does not establish that a v2 Repitan preserves a v1 name.
- `diagrams/sectors.svg:23-61` has all eight v1 labels and ranges; lines69-70 explicitly say functional classification,64 theta values each. It is a v1 diagram, not the canonical Repitan partition.
- `spec/ADDRESSING-LAYERS.md:64-115` distinguishes the v1 and v2 fields. Lines131-158 label the translation informational/approximate, intentionally lossy. The formula139 is `theta_v2=(theta*27)//512+1`, reverse149 is `theta=((theta_v2-1)*512)//27`.
- `MIGRATION_V2.md:44-46` likewise calls the projection intentionally lossy. Line51's phrase “512 semantic sectors →27 Repitans” conflates512 coordinate values with the eight semantic classes elsewhere; do not use that wording as evidence of512 named categories. No edit made.
- `VISION.md:33-40` describes27 Repitans/semantic sector and classification encoded in the address; this is a label convention, not automatic content recognition. VISION:67's broad software/hardware identical-results claim requires the separate binding/hardware evidence, not this pure Python sector trace.
- Existing lifecycle/deprecation disagreement in VISION:139, MIGRATION:75-89 versus ADDRESSING-LAYERS (“neither layer deprecated”) remains the already-open CX-001 issue. Do not choose precedence or reopen/fix it here.

## Consumer map (all rpp/*.py files found by git grep sector)

`git grep -l -i sector -- rpp/*.py` returns16 files:

| File | Relevant lines and use |
|---|---|
| rpp/__init__.py | 18-31 exports the canonical RPPAddress/ThetaSector/coherence/same_sector APIs. It does not export the legacy class as the same definition. |
| rpp/address.py | 96-114 computes the legacy label;135-184 encodes/decodes theta bits. |
| rpp/address_canonical.py | 83-145 Repitan classes;350-353 .sector;498-513 chooses sector center Repitan;557-580 equality/explicit adjacency graph. |
| rpp/cli.py | 40 imports legacy address API;105,163 use addr.sector_name;416ff renders sector explanation. |
| rpp/consent.py | 52-103 v1 Sector+sensitivity;223-224 computes sector/grounding;278-285 diminished reads deny high sectors;292-299 full-consent writes to high sectors need verified identity;302-308 ethereal writes need caller-supplied coherence>=0.4. |
| rpp/consent_header.py | 56-71 is a separate five-state ACSP enum, used by sector_router;254-280 derives it from somatic/verbal fields. 624ff sector usage is demo-only. |
| rpp/extended.py | 126-142 truncates20-bit theta via>>11;145-164 applies the same v1 labels to resulting9-bit theta. This64-bit legacy extension is not the v2 canonical format. |
| rpp/i18n.py | 54-62 and127ff translate/display v1 labels; no routing calculation. |
| rpp/memory_bridge.py | 46-49 chooses v1 theta constants64(Memory),160(Witness),256(Bridge/project);111-142 uses caller theta in legacy encode. Label assignment is chosen by application, not inferred from stored content. Do not instantiate for this trace: it writes local memory state and uses wall-clock. |
| rpp/mesh.py | 47-102 FragmentAddress carries explicit RoutableSector/name;327-331 groups connected nodes by equality;486-495 dispatches sector multicast. No raw theta conversion is implied. |
| rpp/network.py | 41-42 defines8 zones/min3 Hot nodes;280-324 decoded theta drives angular gradient routing;387-408 groups HOT node theta//64 for gap detection. No content meaning is measured. |
| rpp/pma.py | 591ff and598,641 use canonical sector constructor in demo code; no separate partition in the stored PMA algorithm. |
| rpp/resolver.py |151-199 forwards legacy theta to check_consent;221-223 embeds the legacy label in backend route path. |
| rpp/sector_router.py | 24-120 enum and access sets;128-158 actual checks;278-348 admission/fallback;356-391 enum ordinal conversion. |
| rpp/transitions.py | 350-355 ETFGate docstring says GUARDIAN lockdown; this class tracks a Boolean freeze condition rather than computing sector labels. |
| rpp/visual.py | 82-97 reproduces v1 names for address display;251-280 shows the eight v1 intervals and highlights one. |

## Deterministic sweep actually run

A read-only Python script imported current source functions, iterated theta0..511 exactly once, compared `from_components(0,t,0,0).sector_name` with `rpp.consent.Sector.from_theta(t)`, computed only the documented theta projection/reverse, and looked up canonical `ThetaSector.from_theta`.

Command context: `/workspace/venvs/rpp-spec/bin/python - <<'PY' ...` from `/workspace/cx004-prove-out`; no random/time/network/model inputs.

Observed counts:

- legacy address label and consent class agree:512/512.
- legacy class sizes: eight classes,64 each.
- v2 valid Repitan class sizes: CORE3,GENE3,MEMORY4,WITNESS3,DREAM4,BRIDGE3,GUARDIAN4,SHADOW3 (27 total).
- projected v2 labels over512 legacy theta inputs: CORE57,GENE57,MEMORY76,WITNESS57,DREAM76,BRIDGE57,GUARDIAN76,SHADOW56.
- equality of old and projected v2 names:36/512; different476/512.
- v1→v2→v1 theta projection preserves the old v1 class442/512; changes it70/512.
- concrete counterexample: theta64 is legacy Memory; projected theta4 is canonical GENE; reverse theta56 is legacy Gene. The different names are not a claim of bit-format corruption: the translation is explicitly lossy and informational.

A second pure script observed:

- `is_universal_access(BRIDGE)` is True, but `can_access_sector(EMERGENCY_OVERRIDE,BRIDGE,674)` is False.
- `can_access_sector(EMERGENCY_OVERRIDE,VOID,0)` is True (zero/reset special case runs before state matrix).
- Nonzero coherence674 admitted sector counts by state: FULL8,ATTENTIVE4,DIMINISHED3,SUSPENDED2,EMERGENCY1.

These are observed source behaviors, not normative endorsement or a security audit.

## Ordinal conversion warning

`from_legacy_sector` (`sector_router.py:356-373`) maps0..7→1..8 with CORE→CORE, GENE→GENE,...SHADOW→SHADOW. This corresponds to canonical `ThetaSector` enum values, not the actual v1 theta//64 map. The actual v1 ordinal names compared with conversion output are:

| v1 index | v1 label | from_legacy_sector(index).name |
|---:|---|---|
|0|Gene|CORE|
|1|Memory|GENE|
|2|Witness|MEMORY|
|3|Dream|WITNESS|
|4|Bridge|DREAM|
|5|Guardian|BRIDGE|
|6|Emergence|GUARDIAN|
|7|Meta|SHADOW|

All8 names differ if a caller misuses that conversion on v1 ordinal bins. Do not claim generic profile-independent sector compatibility. The code/doc “legacy ThetaSector” can instead mean the zero-based canonical enum preceding the VOID-extended enum. Conservative choice: keep these namespaces explicit; do not modify a shipped map or assert semantic equivalence. `to_legacy_sector(VOID)` returns-1 at389-391 even though its Raises section387 says ValueError; ordinary roundtrip property should cover only the eight regular sectors.

## Useful parent property tests and named mutations

1. Exhaust all512 theta values. Expected label tuple =Gene,Memory,Witness,Dream,Bridge,Guardian,Emergence,Meta indexed bytheta//64; compare actual legacy address and consent APIs. Mutate boundary64→63 or a label to fail.
2. Algebraic partition: eight explicit intervals cover0..511 exactly once, each64. Mutate an endpoint overlap/gap to fail. Combine with bit extraction identity for valid28-bit values; explain why the other19 bits cannot affect sector. Avoid suggesting4096 sampled addresses alone enumerate all2^28.
3. For every valid Repitan1..27, exactly one explicitly stated v2 interval covers it; `.sector` matches. Mutate range7..10 to7..9 to fail.
4. Valid canonical sector constructor roundtrips all8 regular names via centers [2,5,8,12,15,19,22,26]. Exclude reserved/sentinel enum classes: create_from_sector(META/INVERSE) deliberately defaults to DREAM at509-513. Mutate center formula or fallback to fail ordinary checks.
5. Record actual lossy correspondence as a diagnostic, not falsely require universal name equality. Fix the known theta64→4→56 counterexample in an evidence test (changing the documented projection multiplier27 would fail).
6. Exhaust five consent states×nine sector requests×coherence integer0..674 (30,375 calls): normal-sector admission is independent of score; only VOID changes atzero. Static `get_accessible_sectors` lacks coherence input and is not a complete runtime admission result. Mutate VOID test0→137 or grant BRIDGE in emergency to fail observed-behavior checks.
7. With `allow_fallback=False`, restricted requests can deny; with fallback=True they route GUARDIAN and set is_redirected. “granted” after fallback does not mean the requested sector was authorized. Mutate fallback order or granted flag to fail.

## Findings and verdict suggestion

MEDIUM: there is no single profile-independent sector number/name: v1 and v2 taxonomies differ, and the documented lossy projection loses both detail and some v1 class boundaries. Bare “Sector4” is not meaningful without profile/context.

MEDIUM: “BRIDGE universal” metadata/helper is not universal under emergency admission; the static accessible-set helper also omits the VOID coherence condition. The stricter choice is actual can_access_sector/route_to_sector checks, not explanatory predicates; record the exceptions rather than resolve core semantics.

LOW: ordinal converter name “legacy” is ambiguous; MIGRATION's512 semantic-sector wording means512 coordinate values, not512 classes. No source edit made.

Suggested sector verdict: **partly proved** overall. The within-profile deterministic partition is well supported by a complete theta-domain sweep and the extraction algebra, and it has actual consent/path/coverage consumers. Semantic truth of content labels and cross-profile name stability are not established. Keep the webpage readout absent until the owner accepts a precise profile-tagged application mapping.

Plain words a person could be shown, only when the app assigns that category: “The category this application assigned to the item.” Engineer line: “A profile-tagged, deterministic theta partition supplies a label for consent lookup and routing; it does not classify payload content or measure a physical state.”

No CX-001 steward item was decided: radius projection alternatives, TTL, T2 bounds and physical enforcement retain their prior unresolved status. This trace uses only theta for cross-layer diagnostics, deliberately leaving radius out.
