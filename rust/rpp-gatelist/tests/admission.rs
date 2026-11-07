use ed25519_dalek::{Signer, SigningKey};
use rand_core::{OsRng, RngCore};
use rpp_core::mobius32::Mobius32Address;
use rpp_gatelist::{Admission, GateKeeper, GateList, Mode, Refusal, Request, PACKET_LEN};
use std::cell::Cell;

fn signer() -> SigningKey {
    let mut secret = [0; 32];
    OsRng.fill_bytes(&mut secret);
    SigningKey::from_bytes(&secret)
}

fn list(key: &SigningKey, sequence: u64) -> GateList {
    let mut grants = [0; 64];
    grants[12] = 1 << 4; // theta=100, Mobius32 only
    GateList {
        signer: key.verifying_key().to_bytes(),
        audience: [17; 32], // public application namespace, not key material
        sequence,
        expires_at: 200,
        grants,
    }
}

fn signed(key: &SigningKey, list: GateList) -> [u8; PACKET_LEN] {
    list.packet(key.sign(&list.message()).to_bytes())
}

fn keeper(key: &SigningKey, mode: Mode) -> GateKeeper {
    GateKeeper::new(key.verifying_key().to_bytes(), [17; 32], 0, mode).unwrap()
}

fn request(update: Option<&[u8]>, now: u64, theta: i64, consented: bool) -> Request<'_> {
    Request {
        update,
        now,
        address: Mobius32Address::new(1, theta, 170, 2).unwrap(),
        consented,
    }
}

fn attempt(gate: &mut GateKeeper, request: Request<'_>) -> Admission {
    let recorded = Cell::new(None);
    let called = Cell::new(false);
    let result = gate.dispatch(
        request,
        |row| {
            recorded.set(Some(row));
            true
        },
        || {
            assert!(recorded.get().is_some(), "audit precedes operation");
            called.set(true);
        },
    );
    assert_eq!(recorded.get(), Some(result));
    assert_eq!(called.get(), result.dispatched);
    result
}

/// Mutation: omit committing a valid update, or deny a fully valid request.
#[test]
fn valid_update_replaces_all_grants_and_dispatches() {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    let first = signed(&key, list(&key, 1));
    let row = attempt(&mut gate, request(Some(&first), 100, 100, true));
    assert!(row.dispatched);
    assert_eq!(row.sequence, 1);
    let mut next = list(&key, 2);
    next.grants = [0; 64];
    let packet = signed(&key, next);
    gate.update(&packet, 101).unwrap();
    assert_eq!(gate.last_good(), Some(&next));
    assert_eq!(
        attempt(&mut gate, request(None, 102, 100, true)).refusal,
        Some(Refusal::SectorDenied)
    );
}

fn refused_update(mut packet: [u8; PACKET_LEN], expected: Refusal, corrupt: bool) {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    let good = list(&key, 5);
    gate.update(&signed(&key, good), 100).unwrap();
    if corrupt {
        packet = signed(&key, list(&key, 6));
        packet[223] ^= 1;
    }
    assert_eq!(gate.update(&packet, 101), Err(expected));
    assert_eq!(gate.last_good(), Some(&good));
    assert_eq!(gate.sequence(), 5);
    assert!(attempt(&mut gate, request(None, 101, 100, true)).dispatched);
}

/// Mutation: remove strict signature verification; last good must survive.
#[test]
fn bad_signature_is_refused_without_replacing_last_good() {
    refused_update([0; PACKET_LEN], Refusal::BadSignature, true);
}

/// Mutation: trust the supplied signer instead of the independently pinned key.
#[test]
fn unknown_key_is_refused_without_replacing_last_good() {
    let outsider = signer();
    refused_update(
        signed(&outsider, list(&outsider, 6)),
        Refusal::UnknownKey,
        false,
    );
}

/// Mutations: replace <= with <, or remove the rising sequence guard.
#[test]
fn equal_lower_and_zero_sequences_preserve_the_last_good() {
    let key = signer();
    for sequence in [0, 4, 5] {
        let mut gate = keeper(&key, Mode::Enforce);
        let good = list(&key, 5);
        gate.update(&signed(&key, good), 100).unwrap();
        let packet = signed(&key, list(&key, sequence));
        assert_eq!(gate.update(&packet, 101), Err(Refusal::SequenceNotRising));
        assert_eq!(gate.last_good(), Some(&good));
        assert_eq!(gate.sequence(), 5);
    }
    let mut gate = keeper(&key, Mode::Enforce);
    assert_eq!(
        gate.update(&signed(&key, list(&key, 0)), 100),
        Err(Refusal::SequenceNotRising)
    );
}

/// Mutations: remove expiry validation, or allow expiry == current time.
#[test]
fn expired_update_and_expiry_boundary_preserve_the_last_good() {
    let key = signer();
    for expiry in [0, 100, 101] {
        let mut gate = keeper(&key, Mode::Enforce);
        let good = list(&key, 1);
        gate.update(&signed(&key, good), 100).unwrap();
        let mut stale = list(&key, 2);
        stale.expires_at = expiry;
        assert_eq!(
            gate.update(&signed(&key, stale), 101),
            Err(Refusal::Expired)
        );
        assert_eq!(gate.last_good(), Some(&good));
        assert_eq!(gate.sequence(), 1);
    }
}

/// Mutation: verify a subset of the signed fields, accepting tampered grants.
#[test]
fn every_message_region_is_authenticated() {
    let key = signer();
    let original = signed(&key, list(&key, 1));
    for offset in [80, 88, 96, 159, 160, 223] {
        let mut packet = original;
        packet[offset] ^= 1;
        let mut gate = keeper(&key, Mode::Enforce);
        assert_eq!(gate.update(&packet, 100), Err(Refusal::BadSignature));
        assert_eq!(gate.last_good(), None);
        assert_eq!(gate.sequence(), 0);
    }
}

/// Mutations: remove the domain/length check or permit another audience.
#[test]
fn malformed_domain_length_and_wrong_audience_are_refused() {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    let packet = signed(&key, list(&key, 1));
    for len in [0, 15, 159, 223] {
        assert_eq!(gate.update(&packet[..len], 100), Err(Refusal::Malformed));
    }
    let mut oversize = packet.to_vec();
    oversize.push(0);
    assert_eq!(gate.update(&oversize, 100), Err(Refusal::Malformed));
    let mut bad = packet;
    bad[0] ^= 1;
    assert_eq!(gate.update(&bad, 100), Err(Refusal::Malformed));
    let mut other = list(&key, 1);
    other.audience[0] ^= 1;
    assert_eq!(
        gate.update(&signed(&key, other), 100),
        Err(Refusal::WrongAudience)
    );
}

/// Mutation: ignore the persisted sequence floor, allowing restart replay.
#[test]
fn restart_floor_and_max_sequence_cannot_be_rolled_back() {
    let key = signer();
    let mut gate =
        GateKeeper::new(key.verifying_key().to_bytes(), [17; 32], 5, Mode::Enforce).unwrap();
    assert_eq!(
        gate.update(&signed(&key, list(&key, 5)), 100),
        Err(Refusal::SequenceNotRising)
    );
    gate.update(&signed(&key, list(&key, u64::MAX)), 100)
        .unwrap();
    assert_eq!(
        gate.update(&signed(&key, list(&key, 0)), 101),
        Err(Refusal::SequenceNotRising)
    );
}

/// Mutations: accept weak trust roots or hide the explicit mode labels.
#[test]
fn weak_pin_is_rejected_and_modes_have_distinct_visible_labels() {
    assert!(matches!(
        GateKeeper::new([0; 32], [17; 32], 0, Mode::Enforce),
        Err(Refusal::UnknownKey)
    ));
    assert_eq!(Mode::Enforce.label(), "enforce");
    assert!(Mode::LogOnly.label().contains("log-only"));
    assert_ne!(Mode::Enforce.label(), Mode::LogOnly.label());
}

/// Mutations: skip application expiry, no-list or sector admission guards.
#[test]
fn enforce_never_calls_the_operation_on_missing_stale_or_denied_list() {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    let row = attempt(&mut gate, request(None, 100, 100, true));
    assert_eq!(row.refusal, Some(Refusal::NoList));
    assert!(!row.dispatched);
    gate.update(&signed(&key, list(&key, 1)), 100).unwrap();
    for (now, theta, expected) in [
        (199, 101, Refusal::SectorDenied),
        (200, 100, Refusal::Expired),
        (201, 100, Refusal::Expired),
    ] {
        let row = attempt(&mut gate, request(None, now, theta, true));
        assert_eq!(row.refusal, Some(expected));
        assert!(!row.dispatched);
    }
}

/// Mutation: allow the last good list to hide failure of THIS request's update.
#[test]
fn enforce_refuses_each_bad_update_at_the_operation_boundary() {
    let key = signer();
    let other = signer();
    let mut bad_sig = signed(&key, list(&key, 2));
    bad_sig[223] ^= 1;
    let mut expired = list(&key, 2);
    expired.expires_at = 101;
    for (packet, expected) in [
        (bad_sig, Refusal::BadSignature),
        (signed(&other, list(&other, 2)), Refusal::UnknownKey),
        (signed(&key, list(&key, 0)), Refusal::SequenceNotRising),
        (signed(&key, list(&key, 1)), Refusal::SequenceNotRising),
        (signed(&key, expired), Refusal::Expired),
    ] {
        for mode in [Mode::Enforce, Mode::LogOnly] {
            let mut gate = keeper(&key, mode);
            gate.update(&signed(&key, list(&key, 1)), 100).unwrap();
            let row = attempt(&mut gate, request(Some(&packet), 101, 100, true));
            assert_eq!(row.mode, mode);
            assert_eq!(row.refusal, Some(expected));
            assert_eq!(row.dispatched, mode == Mode::LogOnly);
            assert_eq!(gate.sequence(), 1);
            assert!(attempt(&mut gate, request(None, 102, 100, true)).dispatched);
        }
    }
}

/// Mutation: hide log-only mode/refusals or permit invalid updates into state.
#[test]
fn log_only_is_explicit_visible_and_does_not_accept_bad_updates() {
    let key = signer();
    let mut gate = keeper(&key, Mode::LogOnly);
    assert_eq!(gate.mode(), Mode::LogOnly);
    let row = attempt(&mut gate, request(Some(&[0; PACKET_LEN]), 100, 100, true));
    assert_eq!(row.mode, Mode::LogOnly);
    assert_eq!(row.refusal, Some(Refusal::Malformed));
    assert!(row.dispatched);
    assert_eq!(gate.last_good(), None);
    assert_eq!(gate.sequence(), 0);
}

/// Mutation: allow log-only to bypass the host's independent consent check.
#[test]
fn neither_mode_bypasses_current_consent() {
    let key = signer();
    for mode in [Mode::Enforce, Mode::LogOnly] {
        let mut gate = keeper(&key, mode);
        gate.update(&signed(&key, list(&key, 1)), 100).unwrap();
        let row = attempt(&mut gate, request(None, 101, 100, false));
        assert_eq!(row.refusal, Some(Refusal::NoConsent));
        assert!(!row.dispatched);
    }
}

/// Mutations: advance time before validation or omit rollback refusal.
#[test]
fn invalid_future_update_cannot_poison_clock_and_rollback_is_refused() {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    gate.update(&signed(&key, list(&key, 1)), 100).unwrap();
    let mut bad = signed(&key, list(&key, 2));
    bad[223] ^= 1;
    assert_eq!(gate.update(&bad, u64::MAX), Err(Refusal::BadSignature));
    gate.update(&signed(&key, list(&key, 2)), 101).unwrap();
    assert_eq!(
        gate.update(&signed(&key, list(&key, 3)), 100),
        Err(Refusal::ClockRollback)
    );
    let row = attempt(&mut gate, request(None, 100, 100, true));
    assert_eq!(row.refusal, Some(Refusal::ClockRollback));
    assert!(!row.dispatched);
    assert!(attempt(&mut gate, request(None, 102, 100, true)).dispatched);
}

/// Mutation: ignore audit failure and execute without an observable decision.
#[test]
fn unavailable_audit_refuses_dispatch_in_both_modes() {
    let key = signer();
    for mode in [Mode::Enforce, Mode::LogOnly] {
        let mut gate = keeper(&key, mode);
        gate.update(&signed(&key, list(&key, 1)), 100).unwrap();
        let called = Cell::new(false);
        let row = gate.dispatch(
            request(None, 101, 100, true),
            |_| false,
            || called.set(true),
        );
        assert!(!called.get());
        assert_eq!(row.refusal, Some(Refusal::AuditUnavailable));
        assert!(!row.dispatched);
    }
}

/// Mutation: key admission by phi instead of theta, or misindex edge sectors.
#[test]
fn only_theta_selects_grants_including_both_bitmap_edges() {
    let key = signer();
    let mut gate = keeper(&key, Mode::Enforce);
    let mut allowed = list(&key, 1);
    allowed.grants[0] = 1;
    allowed.grants[63] = 1 << 7;
    gate.update(&signed(&key, allowed), 100).unwrap();
    for theta in [0, 100, 511] {
        for (shell, phi, harmonic) in [(0, 0, 0), (3, 511, 255), (1, 1, 2), (2, 510, 254)] {
            let mut ask = request(None, 101, theta, true);
            ask.address = Mobius32Address::new(shell, theta, phi, harmonic).unwrap();
            assert!(attempt(&mut gate, ask).dispatched);
        }
    }
}
