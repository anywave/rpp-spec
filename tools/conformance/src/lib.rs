#![forbid(unsafe_code)]
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const LATTICEWORKS: &str = "86899f736f751e32603129fcdaf47e4aa313052f";
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(tag = "status", rename_all = "snake_case", deny_unknown_fields)]
pub enum Outcome {
    Bytes { hex: String },
    Reject,
    Valid,
    Unavailable,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub id: String,
    pub profile: String,
    pub json: String,
    pub domain: Option<String>,
    pub expected: Outcome,
}
pub fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(char::from(b"0123456789abcdef"[usize::from(b >> 4)]));
        out.push(char::from(b"0123456789abcdef"[usize::from(b & 15)]));
    }
    out
}
fn bytes(v: impl AsRef<[u8]>) -> Outcome {
    Outcome::Bytes {
        hex: hex(v.as_ref()),
    }
}
pub fn evaluate(c: &Case) -> Result<(Outcome, Option<Value>), String> {
    let v: Value = match serde_json::from_str(&c.json) {
        Ok(v) => v,
        Err(_) => return Ok((Outcome::Reject, None)),
    };
    let result = match c.profile.as_str() {
        "jobcard-json" => {
            let domain = c.domain.as_deref().unwrap_or("d");
            let actual = lw_jobcard::signing_bytes(domain, &v);
            let mut without = v.clone();
            if let Some(m) = without.as_object_mut() {
                m.remove("sig");
            }
            let other = format!("{domain}\n{}", lw_registry::canonical_json(&without));
            if actual != other.as_bytes() {
                return Err("native canonical implementations disagree".into());
            }
            bytes(actual)
        }
        "registry-json" => bytes(lw_registry::canonical_json(&v)),
        _ => return Err(format!("unknown profile: {}", c.profile)),
    };
    Ok((result, None))
}
pub fn corpus(text: &str) -> Result<Vec<Case>, String> {
    if text.len() > 2 * 1024 * 1024 {
        return Err("corpus exceeds 2 MiB".into());
    }
    let mut ids = std::collections::BTreeSet::new();
    let mut cases = Vec::new();
    for line in text.lines().filter(|s| !s.trim().is_empty()) {
        let c: Case = serde_json::from_str(line).map_err(|_| "invalid case schema")?;
        if c.id.is_empty()
            || c.id.len() > 64
            || !c
                .id
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"-_".contains(&b))
            || !ids.insert(c.id.clone())
        {
            return Err("invalid or duplicate case ID".into());
        }
        cases.push(c);
    }
    if cases.is_empty() || cases.len() > 256 {
        return Err("expected 1..256 cases".into());
    }
    Ok(cases)
}
