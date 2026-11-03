use rpp_link::LinkReading;

#[derive(Default)]
pub(crate) struct Measurements {
    samples: [bool; 32],
    used: usize,
    next: usize,
    latest: bool,
    previous_rtt: Option<u64>,
    latency: u64,
    jitter_q4: u128,
}
impl Measurements {
    pub fn observe(&mut self, rtt: Option<u64>) {
        self.samples[self.next] = rtt.is_some();
        self.next = (self.next + 1) % 32;
        self.used = (self.used + 1).min(32);
        self.latest = rtt.is_some();
        if let Some(value) = rtt {
            if let Some(previous) = self.previous_rtt {
                let d = u128::from(value.abs_diff(previous));
                self.jitter_q4 = self.jitter_q4 + d - ((self.jitter_q4 + 8) >> 4);
            }
            self.previous_rtt = Some(value);
            self.latency = value;
        } else {
            self.previous_rtt = None;
            self.latency = 0;
            self.jitter_q4 = 0;
        }
    }
    pub fn reading(&self, tick: u64) -> LinkReading {
        let lost = self.samples[..self.used]
            .iter()
            .filter(|&&success| !success)
            .count();
        LinkReading {
            latency_ms: self.latency,
            loss_ppm: if self.used == 0 {
                1_000_000
            } else {
                (lost * 1_000_000 / self.used) as u32
            },
            jitter_ms: (self.jitter_q4 >> 4).min(u128::from(u64::MAX - 1)) as u64,
            available: self.latest,
            observed: tick,
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    /// Mutation: forget losses or retain a success older than the 32-probe window.
    #[test]
    fn thirty_two_failed_probes_replace_prior_success() {
        let mut m = Measurements::default();
        m.observe(Some(7));
        for _ in 0..31 {
            m.observe(None);
        }
        assert_eq!(m.reading(1).loss_ppm, 968_750);
        m.observe(None);
        let r = m.reading(2);
        assert_eq!(r.loss_ppm, 1_000_000);
        assert!(!r.available);
        assert_eq!(r.observed, 2);
    }
    /// Mutations: integer-ms smoothing, unsigned delta, or stale latency/jitter/history after loss.
    #[test]
    fn rfc3550_fixed_point_jitter_handles_both_rtt_directions() {
        let mut m = Measurements::default();
        m.observe(Some(0));
        for i in 1..=64 {
            m.observe(Some(if i % 2 == 0 { 0 } else { 16 }));
        }
        assert!(m.reading(0).jitter_ms >= 15);
        m.observe(Some(u64::MAX - 1));
        m.observe(Some(0));
        assert!(m.reading(0).jitter_ms < u64::MAX);
        m.observe(Some(64));
        m.observe(None);
        assert_eq!((m.reading(1).latency_ms, m.reading(1).jitter_ms), (0, 0));
        assert!(!m.reading(1).available);
        m.observe(Some(0));
        assert_eq!(m.reading(2).jitter_ms, 0);
    }
}
