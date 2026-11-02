use crate::{Candidate, CostClass, Error, MessageClass, MAX_LINKS};
use core::cmp::Ordering;
use rpp_link::LinkKind;
pub(crate) const DEFAULT_BULK_LOSS_PPM: u32 = 200_000;

pub(crate) fn validate_ceiling(ceiling_ppm: u32) -> Result<(), Error> {
    if ceiling_ppm > 1_000_000 {
        return Err(Error::InvalidLossCeiling);
    }
    Ok(())
}

pub(crate) fn validate(tick: u64, wire_bytes: usize, links: &[Candidate]) -> Result<(), Error> {
    if wire_bytes == 0 {
        return Err(Error::EmptyPayload);
    }
    if links.len() > MAX_LINKS {
        return Err(Error::TooManyLinks);
    }
    for (index, link) in links.iter().enumerate() {
        if !link.reading.valid() || link.reading.observed > tick {
            return Err(Error::InvalidReading);
        }
        if link.mtu == 0 {
            return Err(Error::InvalidMtu);
        }
        if links[..index].iter().any(|prior| prior.id == link.id) {
            return Err(Error::DuplicateId);
        }
    }
    Ok(())
}
pub(crate) fn eligible(
    link: &Candidate,
    class: MessageClass,
    wire_bytes: usize,
    ceiling_ppm: u32,
) -> bool {
    if class == MessageClass::Bulk && link.throughput_kbps == 0 {
        return false;
    }
    if class == MessageClass::Bulk
        && (link.reading.loss_ppm > ceiling_ppm || link.reading.loss_ppm == 1_000_000)
    {
        return false;
    }
    if class != MessageClass::Control
        && (link.kind == LinkKind::Ble || link.cost == CostClass::ControlOnly)
    {
        return false;
    }
    link.reading.available && wire_bytes <= usize::from(link.mtu)
}
pub(crate) fn compare(left: &Candidate, right: &Candidate, class: MessageClass) -> Ordering {
    let throughput = if class == MessageClass::Bulk {
        right.throughput_kbps.cmp(&left.throughput_kbps)
    } else {
        Ordering::Equal
    };
    throughput
        .then_with(|| left.reading.loss_ppm.cmp(&right.reading.loss_ppm))
        .then_with(|| left.reading.latency_ms.cmp(&right.reading.latency_ms))
        .then_with(|| left.reading.jitter_ms.cmp(&right.reading.jitter_ms))
        .then_with(|| left.cost.cmp(&right.cost))
        .then_with(|| left.id.cmp(&right.id))
}
pub(crate) fn best(
    links: &[Candidate],
    class: MessageClass,
    wire_bytes: usize,
    ceiling_ppm: u32,
) -> Option<&Candidate> {
    links
        .iter()
        .filter(|link| eligible(link, class, wire_bytes, ceiling_ppm))
        .min_by(|a, b| compare(a, b, class))
}
/// Stateless ranking; the caller supplies a logical tick shared by observations.
/// Old observations are not expired here: freshness remains caller policy.
pub fn best_link(
    tick: u64,
    class: MessageClass,
    wire_bytes: usize,
    links: &[Candidate],
) -> Result<Option<u32>, Error> {
    best_link_with_ceiling(tick, class, wire_bytes, links, DEFAULT_BULK_LOSS_PPM)
}
/// Configurable bulk loss ceiling in ppm; total loss is always bulk-ineligible.
pub fn best_link_with_ceiling(
    tick: u64,
    class: MessageClass,
    wire_bytes: usize,
    links: &[Candidate],
    ceiling_ppm: u32,
) -> Result<Option<u32>, Error> {
    validate_ceiling(ceiling_ppm)?;
    validate(tick, wire_bytes, links)?;
    Ok(best(links, class, wire_bytes, ceiling_ppm).map(|link| link.id))
}
