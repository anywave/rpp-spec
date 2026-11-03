//! Local TCP framing: the prefix excludes itself and includes the UDP envelope.
use crate::{MAX_DATAGRAM_LEN, VERSION};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameError {
    InvalidLength,
    InvalidEnvelope,
    Truncated,
}
fn valid(wire: &[u8]) -> Result<(), FrameError> {
    if !(2..=MAX_DATAGRAM_LEN).contains(&wire.len()) {
        return Err(FrameError::InvalidLength);
    }
    if wire[0] != VERSION
        || !(1..=4).contains(&wire[1])
        || matches!(wire[1], 1 | 2) && wire.len() != 10
        || wire[1] == 3 && wire.len() != 2 + rpp_control::FRAME_LEN
    {
        return Err(FrameError::InvalidEnvelope);
    }
    Ok(())
}
pub fn encode(envelope: &[u8]) -> Result<Vec<u8>, FrameError> {
    valid(envelope)?;
    let mut output = Vec::with_capacity(envelope.len() + 2);
    output.extend_from_slice(&(envelope.len() as u16).to_be_bytes());
    output.extend_from_slice(envelope);
    Ok(output)
}
/// Decode one frame; trailing bytes belong to the next frame, never this one.
pub fn decode_one(input: &[u8]) -> Result<(&[u8], usize), FrameError> {
    let prefix: [u8; 2] = input
        .get(..2)
        .ok_or(FrameError::Truncated)?
        .try_into()
        .unwrap();
    let size = usize::from(u16::from_be_bytes(prefix));
    if !(2..=MAX_DATAGRAM_LEN).contains(&size) {
        return Err(FrameError::InvalidLength);
    }
    let end = size + 2;
    let wire = input.get(2..end).ok_or(FrameError::Truncated)?;
    valid(wire)?;
    Ok((wire, end))
}
