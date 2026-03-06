# RPP for Real-World Deployment
## Immediate Value Without Spintronic Hardware

**Version:** 1.0.0
**Status:** Active — Deployment / Use Cases
**Audience:** Engineers, architects, compliance teams, product managers
**Last Updated:** 2026-03-04
**License:** CC BY 4.0

---

## The Short Version

RPP is a **consent-aware addressing scheme** that can be dropped into existing
infrastructure today — no new network, no exotic hardware, no protocol migration.

The spintronic physics in the other spec documents describes what RPP becomes at
full capability. This document describes **what RPP is right now**: a software
addressing layer that makes consent intrinsic to data location, not bolted on
as a policy overlay.

The key insight:

```
Conventional:   store data → enforce consent via middleware/policy
                "right to be forgotten" = find all copies and DELETE

RPP:            data's address IS its consent state
                "right to be forgotten" = revoke consent → address expires
                The data is still there. It is simply unreachable.
                No DELETE operation. No audit trail of deletion.
                The address ceased to exist when consent ceased to exist.
```

That is the deployable value. The rest of this document shows how to apply it.

---

## 1. The Problem RPP Solves

Modern data systems have a structural contradiction:

**Data wants a permanent location** (so you can find it again).
**Consent is temporary** (it can be revoked, it expires, it changes).

The current solution is to keep data in permanent locations and add a consent
enforcement layer on top: middleware, access control lists, policy engines,
audit logs. When consent is revoked, you hunt down all copies and delete them.
This is expensive, error-prone, and fundamentally at odds with how distributed
systems work (caches, backups, replicas, CDNs).

RPP dissolves this contradiction: **the address is a function of the consent
state**. When consent changes, the address changes. There is no "location" for
data that lacks consent — the address simply does not resolve. You cannot find
what you cannot address.

This is not philosophical. It maps directly to compliance requirements:

| Requirement | Conventional approach | RPP approach |
|-------------|----------------------|--------------|
| GDPR Art. 17 (Right to erasure) | Find all copies, DELETE each one | Revoke consent → address expires → data unreachable |
| GDPR Art. 7 (Consent conditions) | Consent stored in separate policy DB | Consent encoded in Phi field of address |
| GDPR Art. 25 (Privacy by design) | Privacy as overlay on existing system | Privacy intrinsic to addressing — cannot be separated |
| HIPAA minimum necessary | ACL rules on data store | Phi routing — data only reachable at appropriate consent level |
| CCPA right to opt-out | Flag in user record, middleware checks flag | Phi shift → address no longer routes to that data tier |
| IoT data sovereignty | Per-device policy engine | Shell TTL — device data expires at session end (Shell=0) |

---

## 2. The Four Fields — Plain English

RPP addresses have four fields. Here is what they mean in business terms:

### Shell — How Long Does This Data Exist?

```
Shell=0 (Hot)    → Lives for this session. Gone when the session ends.
                   Use for: live sensor readings, active transaction state,
                   real-time analytics, in-flight API calls

Shell=1 (Warm)   → Lives for this transaction or day.
                   Use for: order processing, payment flows, daily reports,
                   short-term cache

Shell=2 (Cold)   → Lives under this agreement. Expires when the agreement does.
                   Use for: contract-scoped data, subscription data,
                   data shared under a specific consent agreement

Shell=3 (Frozen) → Persists until the data owner explicitly revokes consent.
                   Use for: long-term archives, legal records, identity data
                   that the user has consented to store indefinitely
```

Shell does not just describe where data is stored. It defines **how long the
routing permission survives**. A Shell=0 address resolved in one session is
not valid in the next session. This is enforced by the addressing layer, not
by the application.

### Theta — What Kind of Data Is This?

Theta (9 bits, 0-511) encodes the data type sector. Different theta values route
to different parts of the system:

```
theta 0-63:   Gene / Identity — core identity, credentials, biometric
theta 64-127: Memory / Experience — behavioral history, preferences
theta 128-191: Witness / Observation — audit logs, sensor data, events
theta 192-255: Dream / Speculation — ML predictions, recommendations
theta 256-319: Bridge / Integration — API translations, schema mappings
theta 320-383: Guardian / Protection — consent rules, access policies
theta 384-447: Emergence / Discovery — anomaly detection, novel patterns
theta 448-511: Meta / Self-reference — system metadata, routing state
```

These are conventions, not hard requirements. Your system defines what theta
values mean for your domain. The point is that the address encodes where on
the "data type map" this piece of data lives.

### Phi — What Consent Level Is Required to Access This?

Phi (9 bits, 0-511) encodes the **consent requirement as a continuous spectrum**.
This is the field that makes RPP compliance-relevant:

```
phi=0:          Open access — no consent required (public data)
phi=1-127:      Low consent — minimal conditions (public with attribution)
phi=128-255:    Standard consent — typical terms of service / basic GDPR
phi=256-383:    Elevated consent — sensitive data, explicit opt-in required
phi=384-447:    High consent — medical/financial data, signed consent forms
phi=448-510:    Restricted — research exemptions, legal holds, regulatory
phi=511:        Maximum restriction — maximum consent requirement
```

**Consent is not binary.** An address with phi=200 will route through a node
that handles phi >= 200. The same address will NOT route through a node that
only handles phi <= 100. Consent propagates through the system as a numeric
threshold, not as a policy lookup.

This maps directly to GDPR's consent conditions: the phi value encodes the
consent level the data was collected under. If a user revokes consent, their
phi level drops — the address at the old phi level no longer resolves for them.

### Harmonic — How Should This Data Travel?

Harmonic (8 bits, 0-255) encodes routing priority and storage mode. For most
applications, the default value (128) is appropriate. Advanced use cases can
tune harmonic to:

- Route high-priority data through the fast backbone (harmonic=192-223)
- Mark archival data for direct Cold storage (harmonic=224-255)
- Tune frequency tier for IoT sensor aggregation (harmonic=0-63)

---

## 3. GDPR Deployment — Right to Be Forgotten

### The Problem

GDPR Article 17 requires erasure "without undue delay." In practice, this means:
- Find every copy of user data across every system
- Delete it from hot storage, warm cache, cold archive, backups, logs
- Prove you deleted it (audit trail)
- Do all this without breaking referential integrity in your data model

This is expensive. It is also structurally fragile — you are almost certain
to miss copies.

### The RPP Approach

```
1. On data collection:
   Encode phi based on consent level granted by the user.
   Store the RPP address with the data record.

2. On consent revocation:
   Update the user's consent epoch in the resolver.
   The phi value for that user's data shifts below the routing threshold.
   No DELETE operation.

3. Effect:
   Any request to route to that user's data fails at the resolver.
   The address does not resolve. The data is unreachable.
   From the requester's perspective, the data does not exist.
```

In RPP terms: consent revocation is a **phi shift + epoch increment**. The
resolver refuses to route to addresses below the new phi threshold for that
epoch. All cached routes become stale (they were derived from the previous
epoch's consent state).

### Implementation Pattern

```python
# When user data is collected:
phi = consent_level_to_phi(user.consent_level)
# e.g., "standard GDPR consent" → phi=200

address = encode_rpp_address(
    shell=2,        # Cold — persists for this agreement
    theta=64,       # Memory sector — behavioral data
    phi=phi,        # 200 — standard consent
    harmonic=128,   # standard routing
)
user_record.rpp_address = address

# When user revokes consent:
user.consent_level = ConsentLevel.REVOKED
user.consent_epoch += 1
resolver.invalidate(user.rpp_address, new_epoch=user.consent_epoch)
# → address is now unresolvable. No DELETE needed.

# If user re-grants consent at a lower level:
new_phi = consent_level_to_phi(user.new_consent_level)
# Data at phi=200 is still there in storage.
# New address encodes new consent level.
# Old address remains unresolvable — the data at that consent level is gone.
```

### What "Gone" Means

The data record in your database has not been deleted. The bytes still exist
on disk. But: **there is no valid RPP address that routes to it**. The routing
permission has expired. A request to access that data finds no resolution path
and returns NOT_FOUND — as if the data never existed.

This satisfies "erasure" in the sense that matters: the data is no longer
reachable, no longer processable, no longer "accessible to third parties."
The bytes on disk are unreachable garbage.

If physical deletion is required (e.g., for legal reasons), Shell TTL provides
the hook: data at Shell=2 can be scheduled for physical deletion when the
consent agreement expires. The Shell field is the retention policy.

---

## 4. Healthcare Deployment — Consent-Tier Routing

### The Problem

Medical records have complex, multi-level consent requirements:
- Patient shares data with primary care physician: full access
- Primary care refers to specialist: access to specific records only
- Insurance company: billed procedures only, not diagnoses
- Research team: anonymized aggregate only, no individual records
- Emergency room: full access regardless of prior consent (Break the Glass)

Current systems enforce this with role-based access control + per-record ACLs.
This works but is complex to maintain, audit, and prove to regulators.

### The RPP Approach

Phi encodes the consent tier directly in the address. A record at phi=300
is only routable through nodes authorized for phi >= 300:

```
Patient → PCP:       phi=300 (standard medical consent)
PCP → Specialist:    phi=300 (same consent, referral scope)
To Insurance:        phi=150 (billing data only — lower phi, different theta)
To Research:         phi=80  (anonymized — low phi, aggregate theta sector)
Emergency (Glass):   phi=511 (maximum — override, logged to Hedera)
```

Break the Glass (emergency override) is modeled as a phi=511 address with
Hedera anchoring: the emergency access is permanently recorded, the high phi
value ensures it can only come from authorized emergency nodes.

```python
# Standard medical record
record_address = encode_rpp_address(
    shell=3,      # Frozen — persists until revocation
    theta=64,     # Memory sector — patient history
    phi=300,      # Standard medical consent
    harmonic=128,
)

# Anonymized research view of same record
research_address = encode_rpp_address(
    shell=2,      # Cold — research agreement scope
    theta=128,    # Witness sector — observations/aggregate
    phi=80,       # Low consent — anonymized only
    harmonic=64,  # Background priority
)

# Both addresses point to the same underlying data record.
# The resolver maps each address to the appropriate view.
# No application logic needed — the address encodes the access level.
```

### The Routing Guarantee

A node configured for phi_max=150 (billing data) will never see a phi=300
address resolve through it. The consent level is **enforced at the address layer**,
before the application layer sees the request. There is no code path where a
billing system accidentally accesses a diagnosis record — the address simply
does not route there.

This is "privacy by design" (GDPR Art. 25) in the strict sense: the privacy
constraint is architectural, not policy. You cannot bypass it by misconfiguring
an application.

---

## 5. IoT Data Sovereignty

### The Problem

IoT devices generate continuous streams of sensor data. Who owns it?
Under what conditions can it be accessed? How long does it live?
Current systems: the data goes to the cloud, the cloud owns it.

### The RPP Approach

```
Shell=0 (Hot):  Live sensor reading. Exists only for the current session.
                Readable only by authorized real-time consumers.
                Gone when the device session ends. No persistent storage.

Shell=1 (Warm): Aggregated daily summary. Lives for one day.
                Readable by authorized analytics systems.
                Expires automatically — no DELETE needed.

Shell=2 (Cold): Contract-scoped storage. Lives under the IoT data agreement.
                When the service contract ends, the addresses expire.
                Data becomes unreachable.

Shell=3 (Frozen): Long-term archive. Persists until device owner revokes.
```

The device owner's consent level (phi) determines which systems can access
their data. A device that streams location data at phi=200 will never
route to a system that only has phi=100 authorization.

```python
# IoT sensor publishes live reading
sensor_address = encode_rpp_address(
    shell=0,       # Hot — this session only
    theta=128,     # Witness sector — sensor observation
    phi=device_owner.consent_phi,  # owner's current consent level
    harmonic=192,  # ACTIVE — real-time priority
)

# After session ends: the address is no longer valid.
# The next session gets a new address (different consent epoch).
# Stolen session addresses cannot be replayed — they're already expired.
```

**Stolen session tokens become worthless.** A conventional system leaks a
session token → attacker can replay it indefinitely. An RPP system leaks a
session token → attacker has a Shell=0 Hot address that expired with the
session. No replay attack.

---

## 6. Enterprise: Multi-Tenant Isolation

### The Pattern

In multi-tenant systems, tenant A must never see tenant B's data. Current
approaches: separate databases, schema-per-tenant, or row-level security.
All require application logic to enforce the boundary.

With RPP: each tenant has a consent epoch. Their data is addressed under
that epoch. Cross-epoch addresses do not resolve. Tenant isolation is
architectural.

```python
# Tenant A's data
tenant_a_address = encode_rpp_address(
    shell=2,
    theta=64,
    phi=tenant_a.phi_level,
    harmonic=128,
)
# Routed under tenant_a.consent_epoch

# Tenant B's data — different epoch
tenant_b_address = encode_rpp_address(
    shell=2,
    theta=64,
    phi=tenant_b.phi_level,
    harmonic=128,
)
# Routed under tenant_b.consent_epoch

# Same theta, same phi, different epoch → different address → no cross-routing
```

Tenant B's resolver instance operates under tenant B's consent epoch. A
request from tenant A resolves to nothing in tenant B's epoch. The isolation
is not enforced by the application — it is enforced by the addressing layer.

---

## 7. Deployment Tiers — Start Here

RPP can be adopted incrementally. You do not need to migrate everything at once.
You do not need spintronic hardware. You need:

1. An encoder (30 lines of Python/Go/JS — already in spec/SPEC.md)
2. A resolver (RESOLVER.md reference implementation)
3. A storage backend you already have (File, S3, Redis, PostgreSQL)

### Tier 0: Address Your Data (Week 1)

Add RPP addresses to existing data records. No behavior change — just add the
address as an additional field. Get familiar with the encoding:

```python
from rpp import encode_rpp_address

# Add to any existing record
record['rpp_address'] = encode_rpp_address(
    shell=2,      # Cold — persists for agreement duration
    theta=64,     # Memory sector
    phi=200,      # Standard consent
    harmonic=128, # Standard routing
)
```

### Tier 1: Consent-Gated Resolver (Week 2-3)

Replace direct data lookups with resolver-mediated lookups. The resolver
checks phi before returning a location:

```python
from rpp.resolver import RPPResolver, FileBackend

resolver = RPPResolver(backend=FileBackend("/data"))

# Old code:
data = db.get(record_id)

# New code:
location = resolver.resolve(record['rpp_address'],
                            requester_phi=current_user.phi_level)
data = load_from(location)
# If phi insufficient: raises ConsentInsufficientError
```

### Tier 2: Shell TTL Enforcement (Week 3-4)

Add TTL enforcement per Shell tier. Hot data expires with sessions.
Warm data expires daily. Cold data expires with agreements:

```python
from rpp.resolver import TTLEnforcer, ShellTier

enforcer = TTLEnforcer(
    shell_ttls={
        ShellTier.HOT:    'session',
        ShellTier.WARM:   '1d',
        ShellTier.COLD:   'agreement_end',
        ShellTier.FROZEN: 'explicit_revocation',
    }
)
# TTL enforcer automatically invalidates expired addresses
# No DELETE operations needed — addresses simply stop resolving
```

### Tier 3: Consent Epoch Management (Month 2)

Add consent epoch tracking. Consent revocation increments the epoch.
All addresses under the old epoch become stale:

```python
# On consent revocation:
user.consent_epoch += 1
resolver.invalidate_epoch(user_id, old_epoch=user.consent_epoch - 1)
# → all of user's old addresses are now unreachable
# → right to erasure satisfied by addressing layer
```

### Tier 4: Multi-Modality (Month 3+)

Add transport modalities beyond your current backend. IPFS for cold storage.
Redis for hot cache. S3 for warm archive. The resolver dispatches to the
right backend based on Shell and modality preference — your application code
does not change.

### What You Never Need to Build

- Routing table maintenance → emerges from consent field
- Custom delete workflows for GDPR → address expiry handles it
- Cross-tenant isolation middleware → consent epochs handle it
- Session token replay protection → Shell=0 TTL handles it

---

## 8. Compliance Mapping

| RPP concept | GDPR | HIPAA | CCPA | SOC 2 |
|------------|------|-------|------|-------|
| Phi = consent spectrum | Art. 7 (consent conditions) | Minimum necessary | Right to opt-out | Access control |
| Shell = data retention | Art. 5(e) (storage limitation) | 6-year retention | Retention policies | Data lifecycle |
| Address expires on revocation | Art. 17 (right to erasure) | Revocation of auth. | Right to deletion | Data disposal |
| No central registry | Art. 25 (privacy by design) | Safeguards | Data minimization | Least privilege |
| Consent epoch = audit point | Art. 30 (records of processing) | Audit controls | Opt-out tracking | Audit logging |
| Hedera anchor (opt-in) | Art. 5(2) (accountability) | Audit trail | Compliance records | Change management |

---

## 9. Frequently Asked Questions

**"The data is still in storage — how is that erasure?"**

The data is unreachable via the addressing layer. A request for it returns
NOT_FOUND. A court order to "produce the data" would be met with a valid
response: the data cannot be addressed, therefore it cannot be produced. GDPR
Art. 17 requires erasure from the perspective of access — not necessarily
physical bit-level destruction. The Shell TTL provides the hook for physical
deletion on a schedule.

**"What if someone has a cached copy of the address?"**

Cached RPP addresses are derived from a specific consent epoch. When the epoch
increments (on consent revocation), all cached addresses for that epoch become
stale. The resolver rejects them. The cache is worthless — it cannot produce a
valid resolution path. This is why consent_epoch is part of the address derivation.

**"Do I need to deploy a mesh network to use RPP?"**

No. The simplest RPP deployment is a single resolver instance with a File or S3
backend. You get consent-gated addressing, TTL enforcement, and right-to-erasure
semantics without any mesh. The mesh (NETWORK.md) is the full deployment for
high-availability, consent-field propagation across distributed nodes.

**"How does RPP relate to OAuth/JWT/OIDC?"**

OAuth/JWT encodes authorization claims in a token. RPP encodes consent
requirements in the data's address. They are complementary: OAuth can populate
the requester's phi level (their authorization claim), which the RPP resolver
uses to decide whether to route the request. RPP does not replace OAuth — it
adds a second layer where the DATA itself carries its consent requirement,
not just the requester's token.

**"What's the migration path for existing systems?"**

Tier 0 → Tier 4 (Section 7). Start by adding RPP addresses to existing
records alongside your current addressing scheme. When you're comfortable,
route reads through the resolver. You never have to migrate everything at once.

---

## 10. See Also

- [SPEC.md](SPEC.md) — 28-bit address encoding (the 30 lines of code you need)
- [RESOLVER.md](RESOLVER.md) — resolver architecture and transport modalities
- [ADDRESSING-LAYERS.md](ADDRESSING-LAYERS.md) — v1.0 and v2.0 layer relationship
- [NETWORK.md](NETWORK.md) — full consent-field mesh (for distributed deployment)
- [CONTINUITY.md](CONTINUITY.md) — substrate crossing (for advanced use cases)

---

*"The data does not move. The consent does. The address follows the consent.
When the consent is gone, there is no address. When there is no address,
there is no data — for any practical purpose."*

*This specification is released under CC BY 4.0. Attribution required.*
