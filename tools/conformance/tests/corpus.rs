use rpp_conformance::{corpus, evaluate};
const VECTORS: &str = include_str!("../corpus.json");
#[test]
fn kills_changed_pinned_expectation() {
    for case in corpus(VECTORS).unwrap() {
        assert_eq!(evaluate(&case).unwrap().0, case.expected, "{}", case.id);
    }
}
#[test]
fn kills_duplicate_corpus_id() {
    let rows: Vec<serde_json::Value> = serde_json::from_str(VECTORS).unwrap();
    assert!(corpus(&serde_json::to_string(&vec![&rows[0], &rows[0]]).unwrap()).is_err());
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
