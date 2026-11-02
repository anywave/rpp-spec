use crate::{Candidate, CostClass, Error, MessageClass, MAX_LINKS};
use core::cmp::Ordering;
use rpp_link::LinkKind;

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
pub(crate) fn eligible(link: &Candidate, class: MessageClass, wire_bytes: usize) -> bool {
    if class == MessageClass::Bulk && link.throughput_kbps == 0 {
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
) -> Option<&Candidate> {
    links
        .iter()
        .filter(|link| eligible(link, class, wire_bytes))
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
    validate(tick, wire_bytes, links)?;
    Ok(best(links, class, wire_bytes).map(|link| link.id))
}
