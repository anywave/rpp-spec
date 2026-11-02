//! Bounded local control fragmentation; see SMALL_MTU_FRAMING.md for wire limits.
//! No authentication is implied by a fragment, tag, or peer identifier.
#![no_std]
#![forbid(unsafe_code)]

use rpp_control::DecodeError;
pub const HEADER_LEN: usize = 5;
pub const WIRE_MAX: usize = 255;
const DISPATCH: u8 = 0xe0;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    InvalidMtu,
    BufferTooSmall,
    InvalidHeader,
    Overlap,
    OutOfBounds,
    TooLarge,
    SlotsFull,
    Expired,
    ClockRollback,
    InvalidTimeout,
    Decode(DecodeError),
}

pub struct Fragmenter<'a, const MAX_LEN: usize = { rpp_control::FRAME_LEN }> {
    data: &'a [u8],
    tag: u16,
    mtu: usize,
    offset: usize,
}
impl<'a, const MAX_LEN: usize> Fragmenter<'a, MAX_LEN> {
    pub fn new(data: &'a [u8], tag: u16, mtu: usize) -> Result<Self, Error> {
        if mtu <= HEADER_LEN {
            return Err(Error::InvalidMtu);
        }
        if MAX_LEN > WIRE_MAX || data.len() > MAX_LEN {
            return Err(Error::TooLarge);
        }
        if data.is_empty() {
            return Err(Error::InvalidHeader);
        }
        Ok(Self {
            data,
            tag,
            mtu,
            offset: 0,
        })
    }
    /// A short caller buffer is rejected without advancing the fragment cursor.
    pub fn write_next(&mut self, output: &mut [u8]) -> Result<Option<usize>, Error> {
        if self.offset == self.data.len() {
            return Ok(None);
        }
        let count = (self.mtu - HEADER_LEN).min(self.data.len() - self.offset);
        let length = HEADER_LEN + count;
        if output.len() < length {
            return Err(Error::BufferTooSmall);
        }
        output[0] = DISPATCH | ((self.data.len() >> 8) as u8);
        output[1] = self.data.len() as u8;
        output[2..4].copy_from_slice(&self.tag.to_be_bytes());
        output[4] = self.offset as u8;
        output[HEADER_LEN..length].copy_from_slice(&self.data[self.offset..self.offset + count]);
        self.offset += count;
        Ok(Some(length))
    }
}
