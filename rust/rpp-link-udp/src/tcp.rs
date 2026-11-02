use crate::{framed, measure::Measurements, Config, Counters, Error, Received, VERSION};
use rpp_control::{NodeId, VerifiedControlFrame, Verifier};
use rpp_link::{DataOutcome, LinkAdapter, LinkKind, LinkReading};
use std::{
    collections::VecDeque,
    io::{self, Read, Write},
    net::{Shutdown, SocketAddr, TcpStream},
    time::{Duration, Instant},
};

pub(crate) fn validate(peer: SocketAddr, kind: LinkKind, timeout: Duration) -> Result<(), Error> {
    if !peer.ip().is_loopback() {
        return Err(Error::PlainUnderlayRefused);
    }
    Config::new(peer, peer, kind, timeout).map(|_| ())
}
fn invalid(message: &str) -> Error {
    io::Error::new(io::ErrorKind::InvalidData, message).into()
}
/// Each call consumes part of ONE absolute budget, never a fresh chunk budget.
fn transfer_chunks(
    bytes: &mut [u8],
    deadline: Instant,
    mut now: impl FnMut() -> Instant,
    mut step: impl FnMut(&mut [u8], Duration) -> io::Result<usize>,
) -> io::Result<()> {
    let mut used = 0;
    while used < bytes.len() {
        let budget = deadline
            .checked_duration_since(now())
            .filter(|value| !value.is_zero())
            .ok_or_else(|| io::Error::new(io::ErrorKind::TimedOut, "frame deadline"))?;
        match step(&mut bytes[used..], budget) {
            Ok(0) => {
                return Err(io::Error::new(
                    io::ErrorKind::UnexpectedEof,
                    "incomplete frame",
                ))
            }
            Ok(size) => used += size,
            Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
            Err(error) => return Err(error),
        }
    }
    if now() >= deadline {
        return Err(io::Error::new(
            io::ErrorKind::TimedOut,
            "late frame completion",
        ));
    }
    Ok(())
}
/// Synchronous, single-reader TCP session. No reconnect or application replay.
pub struct TcpAdapter {
    stream: TcpStream,
    kind: LinkKind,
    timeout: Duration,
    closed: bool,
    nonce: u64,
    measurements: Measurements,
    counters: Counters,
    pending: VecDeque<Vec<u8>>,
    echo: Option<(u64, Instant)>,
    window: Instant,
    echoes: u32,
}
impl TcpAdapter {
    pub fn connect(peer: SocketAddr, kind: LinkKind, timeout: Duration) -> Result<Self, Error> {
        validate(peer, kind, timeout)?;
        Self::from_stream(TcpStream::connect_timeout(&peer, timeout)?, kind, timeout)
    }
    /// The caller accepts a connection; both actual endpoints must be loopback.
    pub fn from_stream(
        stream: TcpStream,
        kind: LinkKind,
        timeout: Duration,
    ) -> Result<Self, Error> {
        validate(stream.peer_addr()?, kind, timeout)?;
        validate(stream.local_addr()?, kind, timeout)?;
        stream.set_nodelay(true)?;
        Ok(Self {
            stream,
            kind,
            timeout,
            closed: false,
            nonce: 0,
            measurements: Measurements::default(),
            counters: Counters::default(),
            pending: VecDeque::new(),
            echo: None,
            window: Instant::now(),
            echoes: 0,
        })
    }
    pub fn counters(&self) -> Counters {
        self.counters
    }
    pub fn is_closed(&self) -> bool {
        self.closed
    }
    fn close(&mut self) {
        self.closed = true;
        let _ = self.stream.shutdown(Shutdown::Both);
    }
    fn transfer(&mut self, bytes: &mut [u8], deadline: Instant, write: bool) -> Result<(), Error> {
        if self.closed {
            return Err(io::Error::new(io::ErrorKind::NotConnected, "closed frame stream").into());
        }
        let result = transfer_chunks(bytes, deadline, Instant::now, |remaining, budget| {
            if write {
                self.stream.set_write_timeout(Some(budget))?;
                self.stream.write(remaining)
            } else {
                self.stream.set_read_timeout(Some(budget))?;
                self.stream.read(remaining)
            }
        });
        if result.is_err() {
            self.close();
        }
        result.map_err(Error::from)
    }
    fn send_until(&mut self, tag: u8, body: &[u8], deadline: Instant) -> Result<(), Error> {
        if body.len() > crate::MAX_DATA_LEN {
            return Err(Error::TooLarge);
        }
        let wire = [&[VERSION, tag][..], body].concat();
        let mut frame = framed::encode(&wire).map_err(|_| invalid("invalid outgoing envelope"))?;
        self.transfer(&mut frame, deadline, true)
    }
    fn packet(&mut self, deadline: Instant) -> Result<Vec<u8>, Error> {
        let mut prefix = [0; 2];
        self.transfer(&mut prefix, deadline, false)?;
        let size = usize::from(u16::from_be_bytes(prefix));
        if !(2..=crate::MAX_DATAGRAM_LEN).contains(&size) {
            self.close();
            return Err(invalid("invalid frame length"));
        }
        let mut frame = vec![0; size + 2];
        frame[..2].copy_from_slice(&prefix);
        self.transfer(&mut frame[2..], deadline, false)?;
        if framed::decode_one(&frame).is_err() {
            self.close();
            return Err(invalid("invalid incoming envelope"));
        }
        Ok(frame[2..].to_vec())
    }
    fn internal(&mut self, wire: &[u8], deadline: Instant) -> Result<bool, Error> {
        if !matches!(wire[1], 1 | 2) {
            return Ok(false);
        }
        if wire[1] == 2 {
            return Ok(true);
        }
        let now = Instant::now();
        let nonce = u64::from_be_bytes(wire[2..].try_into().expect("validated probe"));
        if self
            .echo
            .is_some_and(|(_, last)| now.saturating_duration_since(last) >= Duration::from_secs(1))
        {
            self.echo = None;
        }
        if now.saturating_duration_since(self.window) >= Duration::from_secs(1) {
            self.window = now;
            self.echoes = 0;
        }
        if self.echo.is_some_and(|(last, _)| nonce <= last) || self.echoes >= 32 {
            self.counters.echo_limited = self.counters.echo_limited.saturating_add(1);
            return Ok(true);
        }
        self.echo = Some((nonce, now));
        self.echoes += 1;
        self.send_until(2, &wire[2..], deadline)?;
        self.counters.echoes = self.counters.echoes.saturating_add(1);
        Ok(true)
    }
    pub fn receive<V: Verifier + ?Sized>(
        &mut self,
        recipient: &NodeId,
        verifier: &V,
    ) -> Result<Option<Received>, Error> {
        let deadline = Instant::now() + self.timeout;
        let wire = match self.pending.pop_front() {
            Some(wire) => wire,
            None => self.packet(deadline)?,
        };
        if self.internal(&wire, deadline)? {
            return Ok(None);
        }
        if wire[1] == 3 {
            return Ok(match rpp_control::decode(&wire[2..], recipient, verifier) {
                Ok(frame) => Some(Received::Control(frame)),
                Err(_) => {
                    self.counters.refused_control = self.counters.refused_control.saturating_add(1);
                    None
                }
            });
        }
        Ok(Some(Received::Data(wire[2..].to_vec())))
    }
}
impl LinkAdapter for TcpAdapter {
    type Error = Error;
    fn kind(&self) -> LinkKind {
        self.kind
    }
    fn read(&mut self, tick: u64) -> Result<LinkReading, Error> {
        self.nonce = self.nonce.checked_add(1).ok_or(Error::NonceExhausted)?;
        let nonce = self.nonce.to_be_bytes();
        let start = Instant::now();
        let deadline = start + self.timeout;
        let mut sample = None;
        let result = (|| -> Result<(), Error> {
            self.send_until(1, &nonce, deadline)?;
            loop {
                let wire = self.packet(deadline)?;
                if wire[1] == 2 && wire[2..] == nonce {
                    sample = Some(start.elapsed().as_millis().min(u128::from(u64::MAX - 1)) as u64);
                    break;
                }
                if self.internal(&wire, deadline)? {
                    continue;
                }
                if self.pending.len() < 4 {
                    self.pending.push_back(wire);
                } else {
                    self.counters.queue_full = self.counters.queue_full.saturating_add(1);
                }
            }
            Ok(())
        })();
        self.measurements.observe(sample);
        result?;
        Ok(self.measurements.reading(tick))
    }
    fn send_verified_control_frame(&mut self, frame: &VerifiedControlFrame) -> Result<(), Error> {
        self.send_until(3, &frame.encode(), Instant::now() + self.timeout)
    }
    fn send_data(&mut self, payload: &[u8]) -> Result<DataOutcome, Error> {
        self.send_until(4, payload, Instant::now() + self.timeout)?;
        Ok(DataOutcome::Sent)
    }
}

#[cfg(test)]
#[path = "tcp_tests.rs"]
mod tests;
