use crate::{bytes, Case, Outcome};
use rpp_core::overlay::{MeterRow, Status, Traffic};
use serde::Deserialize;
use serde_json::Value;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct FactInput {
    record: lw_registry::Record,
    name: String,
    fact: lw_registry::Fact,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PlanInput {
    input: lw_pool::pool::shard::Input,
    mode: lw_pool::pool::shard::Mode,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Row {
    row: u64,
    tick: String,
    request: u64,
    traffic: String,
    source: String,
    target: String,
    path: String,
    status: String,
    tokens: u64,
    detail: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Proof {
    nonce_b: String,
    id_a: String,
    id_b: String,
}
fn meter(raw: &str) -> Option<Vec<MeterRow>> {
    serde_json::from_str::<Vec<Row>>(raw)
        .ok()?
        .into_iter()
        .map(|r| {
            let tick: i128 = r.tick.parse().ok()?;
            if tick.to_string() != r.tick {
                return None;
            }
            let traffic = match r.traffic.as_str() {
                "data" => Traffic::Data,
                "control" => Traffic::Control,
                "billboard" => Traffic::Billboard,
                _ => return None,
            };
            let status = [
                Status::Ok,
                Status::Failed,
                Status::InvalidInput,
                Status::Denied,
                Status::DeniedSelfTarget,
                Status::NoChannel,
                Status::NoIndependentChannel,
                Status::Delivered,
                Status::HeldUntilSince,
            ]
            .into_iter()
            .find(|s| s.as_str() == r.status)?;
            Some(MeterRow {
                row: r.row,
                tick,
                request: r.request,
                traffic,
                source: r.source,
                target: r.target,
                path: r.path,
                status,
                tokens: r.tokens,
                detail: r.detail,
            })
        })
        .collect()
}
pub fn evaluate(c: &Case, v: Value) -> Result<(Outcome, Option<Value>), String> {
    let outcome = match c.profile.as_str() {
        "jobcard-attempt" => match serde_json::from_str::<lw_jobcard::Attempt>(&c.json) {
            Ok(a) => bytes(lw_jobcard::signing_bytes("lw-jobcard/attempt/draft-v0", &a)),
            Err(_) => Outcome::Reject,
        },
        "registry-fact" => match serde_json::from_str::<FactInput>(&c.json) {
            Ok(f) => bytes(lw_registry::fact_message(&f.record, &f.name, &f.fact)),
            Err(_) => Outcome::Reject,
        },
        "plan-json" => {
            let p = serde_json::from_str::<PlanInput>(&c.json)
                .ok()
                .and_then(|p| lw_pool::pool::shard::plan(&p.input, p.mode).ok());
            return Ok(match p {
                Some(p) => (
                    bytes(p.canonical_json().map_err(|_| "plan canonicalization")?),
                    Some(Value::String(
                        serde_json::to_string(&p).map_err(|_| "plan serialization")?,
                    )),
                ),
                None => (Outcome::Reject, None),
            });
        }
        "meter-csv" => match meter(&c.json) {
            Some(rows) => bytes(rpp_core::overlay::serialize_csv(&rows)),
            None => Outcome::Reject,
        },
        "overlay-csv" | "overlay-md" | "overlay-json" => {
            let a = rpp_core::scenarios::artifacts();
            bytes(match c.profile.as_str() {
                "overlay-csv" => a.csv,
                "overlay-md" => a.markdown,
                _ => a.json,
            })
        }
        "lend-proof" => match serde_json::from_str::<Proof>(&c.json) {
            Ok(p)
                if [&p.nonce_b, &p.id_a, &p.id_b].iter().all(|s| {
                    s.len() == 64
                        && s.bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
                }) =>
            {
                bytes(format!(
                    "lw-link lend-key v1|{}|{}|{}",
                    p.nonce_b, p.id_a, p.id_b
                ))
            }
            _ => Outcome::Reject,
        },
        "handoff" => {
            let names = [
                "job_id",
                "attempt_id",
                "worker",
                "slot",
                "epoch",
                "fence",
                "component",
                "result_sha256",
            ];
            if v.as_array().is_some_and(|rows| {
                !rows.is_empty()
                    && rows.iter().all(|r| {
                        r.as_object().is_some_and(|r| {
                            r.contains_key("job_id")
                                && r.iter().all(|(k, v)| {
                                    names.contains(&k.as_str()) && !v.is_array() && !v.is_object()
                                })
                        })
                    })
            }) {
                Outcome::Valid
            } else {
                Outcome::Reject
            }
        }
        _ => return Err("profile unavailable; shared index has no adopted byte rule".into()),
    };
    Ok((outcome, None))
}
