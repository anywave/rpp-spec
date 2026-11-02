use crate::{Error, DISPATCH, HEADER_LEN, WIRE_MAX};
use rpp_control::{decode, NodeId, VerifiedControlFrame, Verifier};

#[derive(Clone, Copy)]
struct Slot<const N: usize> {
    peer: NodeId,
    tag: u16,
    total: usize,
    covered: usize,
    deadline: u64,
    active: bool,
    bytes: [u8; N],
    seen: [bool; N],
}
impl<const N: usize> Slot<N> {
    const EMPTY: Self = Self {
        peer: [0; 16],
        tag: 0,
        total: 0,
        covered: 0,
        deadline: 0,
        active: false,
        bytes: [0; N],
        seen: [false; N],
    };
}

#[derive(Clone, Copy)]
struct Completed {
    peer: NodeId,
    tag: u16,
    until: u64,
    valid: bool,
}
impl Completed {
    const EMPTY: Self = Self {
        peer: [0; 16],
        tag: 0,
        until: 0,
        valid: false,
    };
}

/// Fixed slots; completed bytes are available only through verified decoding.
/// `peer` must be bound by the caller to its actual ingress peer/link context.
pub struct Reassembler<const SLOTS: usize, const MAX_LEN: usize = { rpp_control::FRAME_LEN }> {
    slots: [Slot<MAX_LEN>; SLOTS],
    timeout: u64,
    clock: Option<u64>,
    completed: [Completed; 2],
}
impl<const SLOTS: usize, const MAX_LEN: usize> Reassembler<SLOTS, MAX_LEN> {
    pub fn new(timeout: u64) -> Result<Self, Error> {
        if MAX_LEN == 0 || MAX_LEN > WIRE_MAX {
            return Err(Error::TooLarge);
        }
        if timeout == 0 {
            return Err(Error::InvalidTimeout);
        }
        Ok(Self {
            slots: [Slot::EMPTY; SLOTS],
            timeout,
            clock: None,
            completed: [Completed::EMPTY; 2],
        })
    }
    pub fn retained_slots(&self) -> usize {
        self.slots.iter().filter(|slot| slot.active).count()
    }
    pub fn push<V: Verifier + ?Sized>(
        &mut self,
        peer: NodeId,
        input: &[u8],
        tick: u64,
        recipient: &NodeId,
        verifier: &V,
    ) -> Result<Option<VerifiedControlFrame>, Error> {
        if self.clock.is_some_and(|previous| tick < previous) {
            return Err(Error::ClockRollback);
        }
        if input.len() <= HEADER_LEN || input[0] & 0xf8 != DISPATCH {
            return Err(Error::InvalidHeader);
        }
        let total = (((input[0] & 7) as usize) << 8) | input[1] as usize;
        if total > MAX_LEN || total > WIRE_MAX {
            return Err(Error::TooLarge);
        }
        let tag = u16::from_be_bytes([input[2], input[3]]);
        let offset = input[4] as usize;
        let data = &input[HEADER_LEN..];
        if total == 0 || offset.checked_add(data.len()).is_none_or(|end| end > total) {
            return Err(Error::OutOfBounds);
        }
        if self
            .completed
            .iter()
            .any(|key| key.valid && key.peer == peer && key.tag == tag && tick < key.until)
        {
            return Err(Error::RecentlyCompleted);
        }
        let existing = self
            .slots
            .iter()
            .position(|s| s.active && s.peer == peer && s.tag == tag);
        if let Some(index) = existing {
            if tick >= self.slots[index].deadline {
                self.slots[index] = Slot::EMPTY;
                self.clock = Some(tick);
                return Err(Error::Expired);
            }
            if self.slots[index].total != total {
                return Err(Error::OutOfBounds);
            }
        }
        let index = match existing {
            Some(index) => index,
            None => {
                if let Some(empty) = self.slots.iter().position(|s| !s.active) {
                    empty
                } else if let Some(expired) = self.slots.iter().position(|s| tick >= s.deadline) {
                    let peer = self.slots[expired].peer;
                    let tag = self.slots[expired].tag;
                    self.slots[expired] = Slot::EMPTY;
                    self.clock = Some(tick);
                    return Err(Error::ExpiredKey { peer, tag });
                } else {
                    return Err(Error::SlotsFull);
                }
            }
        };
        let is_new = existing.is_none();
        let deadline = if is_new {
            tick.checked_add(self.timeout)
                .ok_or(Error::InvalidTimeout)?
        } else {
            self.slots[index].deadline
        };
        // Preflight the whole fragment: no prefix write can survive an error.
        if !is_new {
            for (i, byte) in data.iter().enumerate() {
                if self.slots[index].seen[offset + i]
                    && self.slots[index].bytes[offset + i] != *byte
                {
                    return Err(Error::Overlap);
                }
            }
        }
        if is_new {
            self.slots[index] = Slot {
                peer,
                tag,
                total,
                deadline,
                active: true,
                ..Slot::EMPTY
            };
        }
        let slot = &mut self.slots[index];
        let mut added = false;
        for (i, byte) in data.iter().enumerate() {
            if !slot.seen[offset + i] {
                added = true;
                slot.covered += 1;
                slot.seen[offset + i] = true;
                slot.bytes[offset + i] = *byte;
            }
        }
        if !added {
            return Ok(None);
        }
        self.clock = Some(tick);
        if slot.covered == slot.total {
            let until = slot.deadline;
            let result =
                decode(&slot.bytes[..slot.total], recipient, verifier).map_err(Error::Decode);
            self.slots[index] = Slot::EMPTY;
            if result.is_ok() {
                self.completed[0] = self.completed[1];
                self.completed[1] = Completed {
                    peer,
                    tag,
                    until,
                    valid: true,
                };
            }
            return result.map(Some);
        }
        Ok(None)
    }
}

// Cross-target budget gate; the report also records the exact riscv32 size.
const _: () = assert!(core::mem::size_of::<Reassembler<4, 112>>() <= 1200);
#[cfg(target_arch = "riscv32")]
const _: () = assert!(core::mem::size_of::<Reassembler<4, 112>>() == 1144);
