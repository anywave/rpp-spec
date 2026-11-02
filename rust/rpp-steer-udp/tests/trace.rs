use rpp_link::LinkKind;
use rpp_steer::{CostClass, Hysteresis, MessageClass, Reason};
use rpp_steer_udp::{Batch, Bridge, BulkGate, EndpointConfig, Error, LossBands};
use std::{
    io,
    net::{SocketAddr, UdpSocket},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

struct Responder {
    address: SocketAddr,
    stop: Arc<AtomicBool>,
    worker: Option<JoinHandle<io::Result<u64>>>,
}
impl Responder {
    fn start(drops: &'static [u64]) -> Self {
        let socket = UdpSocket::bind("127.0.0.1:0").expect("loopback bind I/O");
        let address = socket.local_addr().expect("loopback address I/O");
        let stop = Arc::new(AtomicBool::new(false));
        let flag = Arc::clone(&stop);
        let worker = thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(4);
            let mut seen = 0_u64;
            let mut bytes = [0; 64];
            while !flag.load(Ordering::Acquire) {
                let remaining = deadline.saturating_duration_since(Instant::now());
                if remaining.is_zero() {
                    return Err(io::Error::new(
                        io::ErrorKind::TimedOut,
                        "responder deadline",
                    ));
                }
                socket.set_read_timeout(Some(remaining.min(Duration::from_millis(10))))?;
                let (size, peer) = match socket.recv_from(&mut bytes) {
                    Ok(value) => value,
                    Err(error)
                        if matches!(
                            error.kind(),
                            io::ErrorKind::WouldBlock | io::ErrorKind::TimedOut
                        ) =>
                    {
                        continue
                    }
                    Err(error) => return Err(error),
                };
                if size != 10 || bytes[..2] != [1, 1] {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "unexpected probe envelope",
                    ));
                }
                let nonce = u64::from_be_bytes(bytes[2..10].try_into().unwrap());
                if nonce != seen + 1 {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        "unexpected probe nonce",
                    ));
                }
                seen = nonce;
                if drops.contains(&nonce) {
                    continue;
                }
                bytes[1] = 2;
                if socket.send_to(&bytes[..10], peer)? != 10 {
                    return Err(io::Error::new(
                        io::ErrorKind::WriteZero,
                        "short probe reply",
                    ));
                }
            }
            Ok(seen)
        });
        Self {
            address,
            stop,
            worker: Some(worker),
        }
    }
    fn close(&mut self) -> io::Result<u64> {
        self.stop.store(true, Ordering::Release);
        match self.worker.take() {
            Some(worker) => worker
                .join()
                .map_err(|_| io::Error::other("responder panic"))?,
            None => Ok(0),
        }
    }
}
impl Drop for Responder {
    fn drop(&mut self) {
        let _ = self.close();
    }
}
fn reject_io<T>(result: &Result<T, Error>) {
    if matches!(result, Err(Error::Udp(rpp_link_udp::Error::Io(_)))) {
        panic!("loopback adapter I/O: {:?}", result.as_ref().err());
    }
}
fn checked<T>(result: Result<T, Error>) -> T {
    reject_io(&result);
    assert!(result.is_ok());
    result.unwrap()
}
struct Fixture {
    bridge: Bridge,
    a: Responder,
    b: Responder,
}
impl Fixture {
    fn start(margin: u64, drops: &'static [u64]) -> Self {
        let mut a = Responder::start(drops);
        let mut b = Responder::start(&[]);
        let configs =
            [(1, a.address, 1000), (2, b.address, 800)].map(|(id, peer, rate)| EndpointConfig {
                id,
                peer,
                local: "127.0.0.1:0".parse().unwrap(),
                kind: LinkKind::Lan,
                timeout: Duration::from_millis(100),
                throughput_kbps: rate,
                cost: CostClass::Unmetered,
            });
        let result = Bridge::bind(
            &configs,
            LossBands {
                lower_ppm: 100_000,
                upper_ppm: 300_000,
            },
            Hysteresis {
                hold_ticks: 3,
                bulk_margin_kbps: margin,
                control_margin_ppm: 0,
                billboard_margin_ppm: 0,
            },
        );
        if result.is_err() {
            a.close().expect("responder A I/O");
            b.close().expect("responder B I/O");
        }
        Self {
            bridge: checked(result),
            a,
            b,
        }
    }
    fn close(&mut self) -> (u64, u64) {
        let a = self.a.close().expect("responder A I/O");
        let b = self.b.close().expect("responder B I/O");
        (a, b)
    }
}
fn trace(margin: u64) -> Vec<Batch> {
    let mut fixture = Fixture::start(margin, &[3, 6, 7]);
    let results: Vec<_> = [2, 2, 4, 2, 21, 1]
        .into_iter()
        .enumerate()
        .map(|(tick, count)| {
            fixture
                .bridge
                .poll(tick as u64, MessageClass::Bulk, 10, &[count, 1])
        })
        .collect();
    let counts = fixture.close();
    for result in &results {
        reject_io(result);
    }
    assert_eq!(counts, (32, 6));
    results.into_iter().map(checked).collect()
}
/// Failing mutations: erase raw readings, invert loss bands, bypass hold, or replace measured selection.
#[test]
fn measured_loss_bands_and_selector_hold_preserve_the_six_phase_trace() {
    let batches = trace(100);
    let losses = [0, 250_000, 375_000, 300_000, 96_774, 93_750];
    let gates = [
        BulkGate::Eligible,
        BulkGate::Eligible,
        BulkGate::AboveUpper,
        BulkGate::AwaitingLower,
        BulkGate::Eligible,
        BulkGate::Eligible,
    ];
    let ids = [1, 1, 2, 2, 2, 1];
    let reasons = [
        Reason::Initial,
        Reason::Best,
        Reason::Ineligible,
        Reason::Best,
        Reason::Hold,
        Reason::Improved,
    ];
    for (tick, batch) in batches.iter().enumerate() {
        assert_eq!(batch.observations.len(), 2);
        let a = batch.observations[0];
        let b = batch.observations[1];
        assert_eq!(
            (a.candidate.id, a.candidate.reading.loss_ppm),
            (1, losses[tick])
        );
        assert!(a.candidate.reading.available);
        assert_eq!(a.candidate.reading.observed, tick as u64);
        assert_eq!(a.bulk_gate, gates[tick]);
        assert_eq!((b.candidate.id, b.candidate.reading.loss_ppm), (2, 0));
        assert!(b.candidate.reading.available);
        assert_eq!(b.candidate.reading.observed, tick as u64);
        assert_eq!(b.bulk_gate, BulkGate::Eligible);
        assert_eq!(batch.decision.link_id, Some(ids[tick]));
        assert_eq!(batch.decision.reason, reasons[tick]);
    }
}
/// Failing mutation: replace the caller's201kbps margin with100 so the final200kbps improvement switches.
#[test]
fn caller_bulk_margin_201_keeps_the_final_endpoint() {
    let batches = trace(201);
    assert_eq!(batches[5].decision.link_id, Some(2));
    assert_eq!(batches[5].decision.reason, Reason::Margin);
}
/// Failing mutations: probe before rollback/batch/payload checks, or advance clock on rejected future inputs.
#[test]
fn rollback_and_invalid_future_batches_do_not_probe() {
    let mut fixture = Fixture::start(100, &[]);
    let first = fixture.bridge.poll(5, MessageClass::Bulk, 10, &[1, 1]);
    let rollback = fixture.bridge.poll(4, MessageClass::Bulk, 10, &[1, 1]);
    let batch = fixture.bridge.poll(100, MessageClass::Bulk, 10, &[0, 1]);
    let empty = fixture.bridge.poll(100, MessageClass::Bulk, 0, &[1, 1]);
    let final_poll = fixture.bridge.poll(6, MessageClass::Bulk, 10, &[1, 1]);
    let counts = fixture.close();
    for result in [&first, &rollback, &batch, &empty, &final_poll] {
        reject_io(result);
    }
    assert_eq!(counts, (2, 2));
    assert_eq!(checked(first).observations[0].candidate.reading.observed, 5);
    assert!(matches!(
        rollback,
        Err(Error::Steer(rpp_steer::Error::ClockRollback))
    ));
    assert!(matches!(batch, Err(Error::InvalidBatch)));
    assert!(matches!(
        empty,
        Err(Error::Steer(rpp_steer::Error::EmptyPayload))
    ));
    assert_eq!(
        checked(final_poll).observations[0]
            .candidate
            .reading
            .observed,
        6
    );
}
