use std::process::{Command, Output};
const REFERENCE: &str = include_str!("../reference.mjs");
fn run(args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_rpp-conformance"))
        .args(args)
        .output()
        .unwrap()
}
fn mutant(before: &str, after: &str) -> Output {
    mutant_for("jobcard-json", before, after)
}
fn mutant_for(profile: &str, before: &str, after: &str) -> Output {
    assert_eq!(REFERENCE.matches(before).count(), 1);
    let script = REFERENCE.replace(before, after);
    run(&[
        "--profile",
        profile,
        "--candidate",
        "node",
        "--candidate-arg",
        "--input-type=module",
        "--candidate-arg",
        "--eval",
        "--candidate-arg",
        &script,
    ])
}
#[test]
fn kills_native_byte_rule_drift() {
    let result = run(&[]);
    assert!(
        result.status.success(),
        "{}",
        String::from_utf8_lossy(&result.stderr)
    );
    let value: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
    assert_eq!(value["failed"], 0);
    assert_eq!(
        value["cases"],
        rpp_conformance::corpus(include_str!("../corpus.json"))
            .unwrap()
            .len()
    );
}
#[test]
fn kills_utf16_key_sort() {
    assert_eq!(
        mutant(
            ".sort((a, b) => Buffer.compare(Buffer.from(a), Buffer.from(b)))",
            ".sort()"
        )
        .status
        .code(),
        Some(1)
    );
}
#[test]
fn kills_prototype_key_loss() {
    assert_eq!(mutant("Object.create(null)", "{}").status.code(), Some(1));
}
#[test]
fn kills_lossy_number_conversion() {
    assert_eq!(
        mutant("return n.toString();", "return String(Number(n));")
            .status
            .code(),
        Some(1)
    );
}
#[test]
fn kills_omitted_outer_signature_removal() {
    assert_eq!(
        mutant(
            "typeof v === 'object') delete v.sig;",
            "typeof v === 'object') void v.sig;"
        )
        .status
        .code(),
        Some(1)
    );
}
#[test]
fn kills_dropped_candidate_rows() {
    assert_eq!(
        run(&[
            "--candidate",
            "node",
            "--candidate-arg",
            "--eval",
            "--candidate-arg",
            "console.log('[]')"
        ])
        .status
        .code(),
        Some(2)
    );
}
#[test]
fn kills_duplicate_candidate_ids() {
    assert_eq!(mutant("id: c.id", "id: 'CB1'").status.code(), Some(2));
}
#[test]
fn kills_removed_csv_quoting() {
    assert_eq!(
        mutant_for(
            "meter-csv",
            r#"const cell = s => /[,"\r\n]/.test(s) ? '"' + s.replaceAll('"', '""') + '"' : s;"#,
            "const cell = s => s;"
        )
        .status
        .code(),
        Some(1)
    );
}
#[test]
fn kills_unavailable_index_success() {
    assert_eq!(run(&["--profile", "index"]).status.code(), Some(2));
}
#[test]
fn kills_removed_output_bound() {
    assert_eq!(mutant("console.log(JSON.stringify(request.map(c => ({ id: c.id, outcome: evaluate(c) }))));", "process.stdout.write(JSON.stringify(request.map(c => ({ id: c.id, outcome: evaluate(c) }))) + ' '.repeat(9*1024*1024));").status.code(), Some(2));
}
