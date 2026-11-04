#![forbid(unsafe_code)]
use rpp_conformance::{corpus, evaluate, hex, Outcome, LATTICEWORKS};
use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs,
    io::Read,
    path::PathBuf,
    process::{Command, Stdio},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

struct Scratch(PathBuf);
impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn scratch() -> Result<Scratch, String> {
    let tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|_| "clock")?
        .as_nanos();
    for n in 0..100 {
        let path =
            std::env::temp_dir().join(format!("rpp-conformance-{}-{tick}-{n}", std::process::id()));
        let mut builder = fs::DirBuilder::new();
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        match builder.create(&path) {
            Ok(()) => return Ok(Scratch(path)),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(_) => return Err("temporary directory unavailable".into()),
        }
    }
    Err("temporary directory collision".into())
}
fn adapter(program: &str, args: &[String], request: &Value) -> Result<Vec<Reply>, String> {
    let tmp = scratch()?;
    let input = tmp.0.join("input");
    let output = tmp.0.join("output");
    let error = tmp.0.join("error");
    fs::write(&input, serde_json::to_vec(request).map_err(|_| "request")?)
        .map_err(|_| "request file")?;
    let mut child = Command::new(program)
        .args(args)
        .stdin(Stdio::from(
            fs::File::open(input).map_err(|_| "request file")?,
        ))
        .stdout(Stdio::from(
            fs::File::create(&output).map_err(|_| "output file")?,
        ))
        .stderr(Stdio::from(
            fs::File::create(&error).map_err(|_| "error file")?,
        ))
        .spawn()
        .map_err(|_| "candidate executable unavailable")?;
    let start = Instant::now();
    loop {
        let over = fs::metadata(&output).map_err(|_| "output")?.len() > 8 * 1024 * 1024
            || fs::metadata(&error).map_err(|_| "error")?.len() > 65536;
        if over || start.elapsed() > Duration::from_secs(20) {
            let _ = child.kill();
            let _ = child.wait();
            return Err("candidate timeout or output limit".into());
        }
        if let Some(status) = child.try_wait().map_err(|_| "candidate wait")? {
            if !status.success() {
                return Err("candidate refused input; no conformance claimed".into());
            }
            break;
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let raw = fs::read(output).map_err(|_| "candidate output")?;
    if raw.len() > 8 * 1024 * 1024 {
        return Err("candidate output limit".into());
    }
    serde_json::from_slice(&raw).map_err(|_| "invalid candidate response".into())
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Reply {
    id: String,
    outcome: Outcome,
}
fn run() -> Result<bool, String> {
    let mut args = std::env::args().skip(1);
    let mut path = None;
    let mut profile = None;
    let mut program = None;
    let mut candidate_args = Vec::new();
    let mut node = "node".to_owned();
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!("cargo run --locked --manifest-path tools/conformance/Cargo.toml -- [--profile NAME]\nDefault: pinned native source versus independent Node byte adapter.\n--vectors FILE reads bounded JSONL cases.\n--node EXE selects Node; --candidate EXE [--candidate-arg ARG] replaces it.\nExit 0: selected cases conform; 1: mismatch; 2: unavailable/invalid input.");
            return Ok(true);
        }
        let value = args.next().ok_or("missing option value")?;
        match arg.as_str() {
            "--vectors" => path = Some(value),
            "--profile" => profile = Some(value),
            "--node" => node = value,
            "--candidate" => program = Some(value),
            "--candidate-arg" => candidate_args.push(value),
            _ => return Err("unknown option".into()),
        }
    }
    if candidate_args.len() > 16 || (program.is_none() && !candidate_args.is_empty()) {
        return Err("invalid candidate arguments".into());
    }
    let text = if let Some(p) = path {
        let mut s = String::new();
        fs::File::open(p)
            .map_err(|_| "vectors unavailable")?
            .take(2 * 1024 * 1024 + 1)
            .read_to_string(&mut s)
            .map_err(|_| "vectors must be UTF-8")?;
        s
    } else {
        include_str!("../corpus.jsonl").to_owned()
    };
    let mut cases = corpus(&text)?;
    if let Some(p) = profile {
        cases.retain(|c| c.profile == p);
    }
    if cases.is_empty() {
        return Err("no cases for selected profile".into());
    }
    let mut request = Vec::new();
    let mut actual = Vec::new();
    for c in &cases {
        let (outcome, value) = evaluate(c)?;
        request.push(
            json!({"id":c.id,"profile":c.profile,"json":c.json,"domain":c.domain,"value":value}),
        );
        actual.push(outcome);
    }
    let (program, candidate_args) = if let Some(p) = program {
        (p, candidate_args)
    } else {
        (
            node,
            vec![
                "--input-type=module".into(),
                "--eval".into(),
                include_str!("../reference.mjs").into(),
            ],
        )
    };
    let reply = adapter(&program, &candidate_args, &Value::Array(request))?;
    if reply.len() != cases.len() {
        return Err("candidate dropped or added rows".into());
    }
    let mut indexed = BTreeMap::new();
    for row in reply {
        if indexed.insert(row.id, row.outcome).is_some() {
            return Err("duplicate candidate ID".into());
        }
    }
    let mut failed = 0;
    let mut rows = Vec::new();
    for (c, native) in cases.iter().zip(actual) {
        let other = indexed.remove(&c.id).ok_or("missing candidate ID")?;
        let pass = native == c.expected && other == native;
        if !pass {
            failed += 1;
        }
        rows.push(json!({"id":c.id,"profile":c.profile,"pass":pass,"expectation":match c.expected { Outcome::Bytes{..}=>"bytes",Outcome::Reject=>"reject",Outcome::Valid=>"valid",Outcome::Unavailable=>"unavailable"}}));
    }
    if !indexed.is_empty() {
        return Err("unknown candidate ID".into());
    }
    println!("{}", serde_json::to_string_pretty(&json!({"status":if failed==0 {"PASS"} else {"FAIL"},"latticeworks":LATTICEWORKS,"corpus_sha256":hex(&Sha256::digest(text.as_bytes())),"cases":rows.len(),"failed":failed,"results":rows})).map_err(|_| "report")?);
    Ok(failed == 0)
}
fn main() {
    match run() {
        Ok(true) => {}
        Ok(false) => std::process::exit(1),
        Err(message) => {
            eprintln!("REFUSED: {message}");
            std::process::exit(2);
        }
    }
}
