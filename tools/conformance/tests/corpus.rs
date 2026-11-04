use rpp_conformance::{corpus, evaluate};
const VECTORS: &str = include_str!("../corpus.jsonl");
#[test]
fn kills_changed_pinned_expectation() {
    for case in corpus(VECTORS).unwrap() {
        assert_eq!(evaluate(&case).unwrap().0, case.expected, "{}", case.id);
    }
}
#[test]
fn kills_duplicate_corpus_id() {
    let line = VECTORS.lines().next().unwrap();
    assert!(corpus(&format!("{line}\n{line}\n")).is_err());
}
#[test]
fn kills_unknown_case_metadata() {
    let line = VECTORS
        .lines()
        .next()
        .unwrap()
        .replacen('{', "{\"extra\":true,", 1);
    assert!(corpus(&line).is_err());
}
