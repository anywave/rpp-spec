use crate::{ranking, Candidate, Error, MessageClass};

/// Absolute margins: loss ppm for control/billboard, measured kbps for bulk.
/// Hold is caller logical ticks; no default silently chooses these policies.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Hysteresis {
    pub hold_ticks: u64,
    pub control_margin_ppm: u32,
    pub bulk_margin_kbps: u64,
    pub billboard_margin_ppm: u32,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Reason {
    Initial,
    Best,
    Hold,
    Margin,
    Improved,
    Ineligible,
    NoChannel,
}
impl Reason {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Initial => "initial",
            Self::Best => "best",
            Self::Hold => "hold",
            Self::Margin => "margin",
            Self::Improved => "improved",
            Self::Ineligible => "ineligible",
            Self::NoChannel => "no-channel",
        }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Decision {
    pub link_id: Option<u32>,
    pub reason: Reason,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct State {
    id: Option<u32>,
    since: u64,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Selector {
    params: Hysteresis,
    states: [State; 3],
    clock: Option<u64>,
    bulk_loss_ceiling_ppm: u32,
}
impl Selector {
    pub fn new(params: Hysteresis) -> Result<Self, Error> {
        Self::with_loss_ceiling(params, ranking::DEFAULT_BULK_LOSS_PPM)
    }
    /// Ceiling in ppm, inclusive except that total loss never carries bulk.
    pub fn with_loss_ceiling(params: Hysteresis, ceiling_ppm: u32) -> Result<Self, Error> {
        ranking::validate_ceiling(ceiling_ppm)?;
        if params.control_margin_ppm > 1_000_000 || params.billboard_margin_ppm > 1_000_000 {
            return Err(Error::InvalidMargin);
        }
        Ok(Self {
            params,
            states: [State { id: None, since: 0 }; 3],
            clock: None,
            bulk_loss_ceiling_ppm: ceiling_ppm,
        })
    }
    /// One atomic underlay payload only. This does not fragment a larger frame.
    /// Invalid input and rollback leave every class and the clock unchanged.
    pub fn choose(
        &mut self,
        tick: u64,
        class: MessageClass,
        wire_bytes: usize,
        links: &[Candidate],
    ) -> Result<Decision, Error> {
        if self.clock.is_some_and(|prior| tick < prior) {
            return Err(Error::ClockRollback);
        }
        ranking::validate(tick, wire_bytes, links)?;
        let index = match class {
            MessageClass::Control => 0,
            MessageClass::Bulk => 1,
            MessageClass::Billboard => 2,
        };
        let state = self.states[index];
        let current = links.iter().find(|link| {
            Some(link.id) == state.id
                && ranking::eligible(link, class, wire_bytes, self.bulk_loss_ceiling_ppm)
        });
        let decision = match (
            current,
            ranking::best(links, class, wire_bytes, self.bulk_loss_ceiling_ppm),
        ) {
            (_, None) => Decision {
                link_id: None,
                reason: Reason::NoChannel,
            },
            (None, Some(best)) => Decision {
                link_id: Some(best.id),
                reason: if state.id.is_some() {
                    Reason::Ineligible
                } else {
                    Reason::Initial
                },
            },
            (Some(current), Some(best)) if current.id == best.id => Decision {
                link_id: Some(current.id),
                reason: Reason::Best,
            },
            (Some(current), Some(best)) => {
                // Primary ranking and accepted-clock monotonicity justify every subtraction.
                debug_assert!(state.since <= tick);
                debug_assert!(
                    class != MessageClass::Bulk || best.throughput_kbps >= current.throughput_kbps
                );
                debug_assert!(
                    class == MessageClass::Bulk
                        || current.reading.loss_ppm >= best.reading.loss_ppm
                );
                let (improvement, margin) = match class {
                    MessageClass::Bulk => (
                        best.throughput_kbps - current.throughput_kbps,
                        self.params.bulk_margin_kbps,
                    ),
                    MessageClass::Control => (
                        u64::from(current.reading.loss_ppm - best.reading.loss_ppm),
                        u64::from(self.params.control_margin_ppm),
                    ),
                    MessageClass::Billboard => (
                        u64::from(current.reading.loss_ppm - best.reading.loss_ppm),
                        u64::from(self.params.billboard_margin_ppm),
                    ),
                };
                if tick - state.since < self.params.hold_ticks {
                    Decision {
                        link_id: Some(current.id),
                        reason: Reason::Hold,
                    }
                } else if improvement < margin {
                    Decision {
                        link_id: Some(current.id),
                        reason: Reason::Margin,
                    }
                } else {
                    Decision {
                        link_id: Some(best.id),
                        reason: Reason::Improved,
                    }
                }
            }
        };
        if decision.link_id != state.id {
            self.states[index] = State {
                id: decision.link_id,
                since: tick,
            };
        }
        self.clock = Some(tick);
        Ok(decision)
    }
}
