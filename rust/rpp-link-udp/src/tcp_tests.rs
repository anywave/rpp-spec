use super::*;
use std::cell::Cell;

/// Mutations: reset the per-chunk deadline, ignore Interrupted time, or accept zero progress.
#[test]
fn chunk_progress_and_interrupts_share_one_absolute_deadline() {
    let start = Instant::now();
    let elapsed = Cell::new(0);
    let mut budgets = Vec::new();
    let result = transfer_chunks(
        &mut [0; 5],
        start + Duration::from_millis(10),
        || start + Duration::from_millis(elapsed.get()),
        |_, budget| {
            budgets.push(budget.as_millis());
            elapsed.set(elapsed.get() + 3);
            Ok(1)
        },
    );
    assert_eq!(
        result.as_ref().err().map(io::Error::kind),
        Some(io::ErrorKind::TimedOut)
    );
    assert_eq!(budgets, [10, 7, 4, 1]);
    let calls = Cell::new(0);
    let result = transfer_chunks(
        &mut [0],
        start + Duration::from_millis(2),
        || start + Duration::from_millis(calls.get()),
        |_, _| {
            calls.set(calls.get() + 1);
            if calls.get() < 4 {
                Err(io::ErrorKind::Interrupted.into())
            } else {
                Ok(1)
            }
        },
    );
    assert_eq!(
        result.as_ref().err().map(io::Error::kind),
        Some(io::ErrorKind::TimedOut)
    );
    assert_eq!(calls.get(), 2);
    let calls = Cell::new(0);
    let result = transfer_chunks(
        &mut [0],
        start + Duration::from_secs(1),
        || start,
        |_, _| {
            calls.set(calls.get() + 1);
            Ok(usize::from(calls.get() > 1))
        },
    );
    assert_eq!(
        result.as_ref().err().map(io::Error::kind),
        Some(io::ErrorKind::UnexpectedEof)
    );
}
/// Mutations: accept nonloopback/mapped addresses, unsupported kinds, or unbounded budgets.
#[test]
fn stream_preflight_refuses_nonloopback_kinds_and_invalid_timeouts_without_io() {
    let good = "127.0.0.1:1".parse().unwrap();
    for text in [
        "192.0.2.1:1",
        "100.64.0.1:1",
        "0.0.0.0:1",
        "[::ffff:127.0.0.1]:1",
    ] {
        assert!(validate(
            text.parse().unwrap(),
            LinkKind::Lan,
            Duration::from_millis(10)
        )
        .is_err());
    }
    for kind in [LinkKind::Ble, LinkKind::Lora] {
        assert!(validate(good, kind, Duration::from_millis(10)).is_err());
    }
    for timeout in [Duration::ZERO, Duration::from_secs(1)] {
        assert!(validate(good, LinkKind::Lan, timeout).is_err());
    }
    assert!(validate(good, LinkKind::Lan, Duration::from_millis(10)).is_ok());
}

/// Mutation: accept a final chunk that completes after the shared frame deadline.
#[test]
fn final_chunk_must_complete_before_the_original_deadline() {
    let start = Instant::now();
    let elapsed = Cell::new(0);
    let result = transfer_chunks(
        &mut [0],
        start + Duration::from_millis(10),
        || start + Duration::from_millis(elapsed.get()),
        |_, _| {
            elapsed.set(11);
            Ok(1)
        },
    );
    assert_eq!(
        result.as_ref().err().map(io::Error::kind),
        Some(io::ErrorKind::TimedOut)
    );
}
