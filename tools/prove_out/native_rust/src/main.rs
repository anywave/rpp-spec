//! Deterministic calls to reviewed ra_core public functions, not a transcription.

use ra_core::gates::{access_level, rac_threshold, AccessResult, COHERENCE_FLOOR};
use ra_core::RacLevel;
use std::fs::File;
use std::io::{BufWriter, Write};

fn adjacent_positive(value: f64, up: bool) -> f64 {
    assert!(value > 0.0 && value.is_finite());
    f64::from_bits(if up { value.to_bits() + 1 } else { value.to_bits() - 1 })
}

fn row(output: &mut BufWriter<File>, level: u8, probe: &str, value: f64) {
    let rac = RacLevel::from_level(level).unwrap();
    let threshold = rac_threshold(rac);
    let result = access_level(value, rac);
    let kind = match result {
        AccessResult::FullAccess => "full",
        AccessResult::PartialAccess(_) => "partial",
        AccessResult::Blocked => "blocked",
    };
    writeln!(output, "{level},{probe},{value:?},{threshold:?},{kind},{:?}", result.alpha()).unwrap();
}

fn main() {
    let destination = std::env::args().nth(1).expect("output CSV path required");
    let mut output = BufWriter::new(File::create(destination).unwrap());
    writeln!(output, "rac,probe,input,threshold,kind,alpha").unwrap();
    for level in 1..=6 {
        let threshold = rac_threshold(RacLevel::from_level(level).unwrap());
        for tick in 0..=1000 {
            row(&mut output, level, &format!("grid-{tick}"), f64::from(tick) / 1000.0);
        }
        for (probe, value) in [
            ("below-floor", adjacent_positive(COHERENCE_FLOOR, false)),
            ("at-floor", COHERENCE_FLOOR),
            ("above-floor", adjacent_positive(COHERENCE_FLOOR, true)),
            ("below-threshold", adjacent_positive(threshold, false)),
            ("at-threshold", threshold),
            ("above-threshold", adjacent_positive(threshold, true)),
        ] {
            row(&mut output, level, probe, value);
        }
    }
    output.flush().unwrap();
    println!("native_rust_grid_rows=6006 native_rust_boundary_rows=36");
}
