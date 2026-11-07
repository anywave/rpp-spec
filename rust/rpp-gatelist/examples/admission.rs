//! Offline smoke application. Throwaway signing key exists only in memory.
use ed25519_dalek::{Signer, SigningKey};
use rand_core::{OsRng, RngCore};
use rpp_core::mobius32::Mobius32Address;
use rpp_gatelist::{Admission, GateKeeper, GateList, Mode, Request};

fn audit(row: Admission) -> bool {
    println!(
        "mode={} refusal={:?} dispatch={} sequence={}",
        row.mode.label(),
        row.refusal,
        row.dispatched,
        row.sequence
    );
    true // A real host durably checkpoints the sequence here before returning true.
}

fn main() {
    let mode = match std::env::args().nth(1).as_deref() {
        Some("enforce") => Mode::Enforce,
        Some("log-only") => Mode::LogOnly,
        _ => {
            eprintln!("Select explicitly: admission enforce | admission log-only");
            std::process::exit(2);
        }
    };
    println!(
        "OFFLINE DEMO: {}; in-memory state, no transport",
        mode.label()
    );
    let mut secret = [0; 32];
    OsRng.fill_bytes(&mut secret);
    let key = SigningKey::from_bytes(&secret);
    let mut gate = GateKeeper::new(key.verifying_key().to_bytes(), [17; 32], 0, mode).unwrap();
    let mut grants = [0; 64];
    grants[12] = 1 << 4;
    let list = GateList {
        signer: key.verifying_key().to_bytes(),
        audience: [17; 32],
        sequence: 1,
        expires_at: 200,
        grants,
    };
    let packet = list.packet(key.sign(&list.message()).to_bytes());
    let address = Mobius32Address::new(1, 100, 170, 2).unwrap();
    // These operations only print: no request is sent anywhere.
    for (label, update, now) in [
        ("valid list", Some(packet.as_slice()), 100),
        ("replayed list", Some(packet.as_slice()), 101),
        ("last good remains active", None, 102),
        ("expired active list", None, 200),
    ] {
        println!("case={label}");
        gate.dispatch(
            Request {
                update,
                address,
                now,
                consented: true,
            },
            audit,
            || println!("local protected operation ran"),
        );
    }
}
