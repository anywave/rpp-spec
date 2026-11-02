"""Bounded actual Rust mutations; all socket tests use loopback only."""
import argparse
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

from tools.esp32_scaffold.mutation_check import Test, assertion_failure, classifier_controls, one_test_summary

ROOT = Path(__file__).resolve().parents[2]
UDP = "rpp-link-udp/src/"
JITTER = ("--lib", "measure::tests::rfc3550_fixed_point_jitter_handles_both_rtt_directions")
KIND = ("--lib", "config::tests::unsupported_kinds_and_unbounded_timeouts_are_refused")
TRAFFIC = ("--test", "traffic")
PROBE = (*TRAFFIC, "probes_are_internal_equal_size_and_each_nonce_gets_at_most_one_reply")
DATA = (*TRAFFIC, "data_is_one_bounded_datagram_and_dispatch_blocks_control_path_data")
FLOW = ("--test", "loopback_pair", "closed_peer_loss_is_measured_and_fleet_selects_the_surviving_endpoint")
CASES = (
    ("plain-address", UDP+"config.rs", "if !allowed(local.ip()) || !allowed(peer.ip())", "if false", ("--lib", "config::tests::address_classes_are_checked_without_opening_sockets"), JITTER),
    ("ble-kind", UDP+"config.rs", "if !matches!(kind, LinkKind::Lan | LinkKind::Wifi | LinkKind::Internet)", "if false", KIND, JITTER),
    ("wire-over-1200", UDP+"socket.rs", "MAX_DATAGRAM_LEN: usize = 1200", "MAX_DATAGRAM_LEN: usize = 1201", DATA, JITTER),
    ("third-socket-parsed", UDP+"socket.rs", "if peer != self.config.peer", "if false", ("--lib", "socket::tests::foreign_packets_are_counted_before_any_parsing_or_verification"), JITTER),
    ("forged-control", "rpp-control/src/lib.rs", "if !verifier.verify(&sender, &header, &signature)", "if false", ("--lib", "socket::tests::only_decoded_verified_control_reaches_the_caller_without_replay_policy"), JITTER),
    ("probe-surfaced", UDP+"socket.rs", "if self.internal(&wire)? {\n            return Ok(None);", "if false && self.internal(&wire)? {\n            return Ok(None);", PROBE, JITTER),
    ("reply-larger", UDP+"socket.rs", "self.send(REPLY, &wire[2..])?", "self.send(REPLY, wire)?", PROBE, JITTER),
    ("reply-non-peer", UDP+"socket.rs", "send_to(&wire[..expected], self.config.peer)", "send_to(&wire[..expected], self.local)", PROBE, JITTER),
    ("loss-not-counted", UDP+"measure.rs", "self.samples[self.next] = rtt.is_some()", "self.samples[self.next] = true", FLOW, JITTER),
    ("reset-is-error", UDP+"socket.rs", "            | io::ErrorKind::ConnectionReset\n", "", ("--lib", "socket::tests::connection_reset_and_timeouts_are_packet_loss_not_errors"), JITTER),
    ("data-on-control", "rpp-link/src/lib.rs", "if path == TrafficPath::Control && matches!(frame, Outbound::Data(_))", "if false && path == TrafficPath::Control && matches!(frame, Outbound::Data(_))", DATA, JITTER),
    ("duplicate-echo", UDP+"socket.rs", "nonce <= last", "nonce < last", PROBE, JITTER),
    ("echo-budget", UDP+"socket.rs", "self.echo_count >= ECHO_BURST", "false", ("--lib", "socket::tests::exhausted_echo_budget_refuses_a_new_nonce"), JITTER),
    ("jitter-erased", UDP+"measure.rs", "self.jitter_q4 = self.jitter_q4 + d - ((self.jitter_q4 + 8) >> 4)", "self.jitter_q4 = 0", JITTER, KIND),
    ("dead-available", UDP+"measure.rs", "self.latest = rtt.is_some()", "self.latest = true", FLOW, KIND),
    ("restart-refused", UDP+"socket.rs", "            self.last_echo = None;\n", "", ("--lib", "socket::tests::restarted_prober_on_same_address_succeeds_after_quiet_gap"), JITTER),
    ("foreign-packet-budget", UDP+"socket.rs", "                loop {\n                    let remaining", "                for _ in 0..32 {\n                    let remaining", ("--lib", "socket::tests::foreign_and_malformed_flood_before_reply_does_not_create_loss"), JITTER),
    ("loss-retains-rtt", UDP+"measure.rs", "            self.latency = 0;\n", "", JITTER, KIND),
    ("loss-retains-jitter", UDP+"measure.rs", "            self.jitter_q4 = 0;\n", "", JITTER, KIND),
    ("loss-retains-previous-rtt", UDP+"measure.rs", "            self.previous_rtt = None;\n", "", JITTER, KIND),
    ("loss-HostUnreachable", UDP+"socket.rs", "            | io::ErrorKind::HostUnreachable\n", "", ("--lib", "socket::tests::connection_reset_and_timeouts_are_packet_loss_not_errors"), JITTER),
    ("loss-NetworkUnreachable", UDP+"socket.rs", "            | io::ErrorKind::NetworkUnreachable\n", "", ("--lib", "socket::tests::connection_reset_and_timeouts_are_packet_loss_not_errors"), JITTER),
    ("loss-NetworkDown", UDP+"socket.rs", "            | io::ErrorKind::NetworkDown\n", "", ("--lib", "socket::tests::connection_reset_and_timeouts_are_packet_loss_not_errors"), JITTER),
    ("loss-ConnectionAborted", UDP+"socket.rs", "            | io::ErrorKind::ConnectionAborted\n", "", ("--lib", "socket::tests::connection_reset_and_timeouts_are_packet_loss_not_errors"), JITTER),

    ("refused-refreshes-gap", UDP+"socket.rs", "        if self.last_echo.is_some_and(|last| nonce <= last)", "        self.last_echo_at = Some(now);\n        if self.last_echo.is_some_and(|last| nonce <= last)", ("--lib", "socket::tests::restarted_prober_on_same_address_succeeds_after_quiet_gap"), JITTER),
    ("stale-notice-ends-probe", UDP+"socket.rs", "Datagram::Dropped | Datagram::Loss => continue,", "Datagram::Dropped => continue,\n                        Datagram::Loss => break,", ("--lib", "socket::tests::stale_reset_and_refused_notice_before_reply_does_not_create_loss"), JITTER),

)


def invoke(cargo, copied, env, selection, log):
    command = [str(cargo), "test", "--manifest-path", str(copied / "Cargo.toml"), "-p", "rpp-link-udp",
               "--offline", "--locked", *selection, "--", "--exact"]
    result = subprocess.run(command, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
    text = result.stdout + result.stderr
    log.write_text(text, encoding="utf-8", newline="\n")
    selected = re.escape(selection[-1])
    if result.returncode == 0 and one_test_summary(result.stdout, 1, 0) and re.search(rf"^test {selected} \.\.\. ok$", result.stdout, re.M):
        return "passed"
    # A caught assertion followed by an unrelated final panic is not a kill.
    last_panic = text.rsplit("panicked at ", 1)[-1].split("\n", 1)
    terminal_assert = len(last_panic) == 2 and re.match(r"assertion (?:failed:|`left (?:==|!=) right` failed)", last_panic[1].lstrip())
    if assertion_failure(result, Test("fixture", selection[-1])) and terminal_assert:
        return "assertion_failure"
    raise RuntimeError("compile/tool/non-assertion failure: " + log.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cargo", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    classifier_controls()
    work = args.work_dir.resolve()
    if work.is_relative_to(ROOT) or args.output.resolve().is_relative_to(ROOT):
        parser.error("write only outside the checkout")
    work.mkdir(parents=True, exist_ok=False)
    copied = work / "rust"
    shutil.copytree(ROOT / "rust", copied, ignore=lambda path, names: set(names) & {"target", ".git"} if Path(path) == ROOT / "rust" else set())
    env = dict(os.environ, CARGO_HOME=str(work / "cargo"), CARGO_TARGET_DIR=str(work / "target"), CARGO_NET_OFFLINE="true")
    version = subprocess.run([str(args.cargo), "--version"], capture_output=True, text=True, encoding="utf-8", env=env, check=True, timeout=30)
    if not version.stdout.startswith("cargo 1.85.1 "):
        raise RuntimeError("select Cargo/RUSTC 1.85.1 explicitly")
    compiler = subprocess.run([env.get("RUSTC", "rustc"), "--version"], capture_output=True, text=True, encoding="utf-8", env=env, check=True, timeout=30)
    if not compiler.stdout.startswith("rustc 1.85.1 "):
        raise RuntimeError("select Rust 1.85.1 explicitly")
    sources = {str(p.relative_to(ROOT)): sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
               for p in (ROOT / "rust").rglob("*") if p.is_file() and p.suffix in {".rs", ".toml", ".lock"}}
    receipts = []
    for name, source, before, after, target, control in CASES:
        path = copied / source
        original = path.read_text(encoding="utf-8")
        if original.count(before) != 1:
            raise RuntimeError("ambiguous mutation: " + name)
        baseline = invoke(args.cargo, copied, env, target, work / (name+"-baseline.log"))
        path.write_text(original.replace(before, after, 1), encoding="utf-8", newline="\n")
        try:
            changed = invoke(args.cargo, copied, env, target, work / (name+"-mutant.log"))
            unaffected = invoke(args.cargo, copied, env, control, work / (name+"-unaffected.log"))
        finally:
            path.write_text(original, encoding="utf-8", newline="\n")
        clean = invoke(args.cargo, copied, env, target, work / (name+"-clean.log"))
        if (baseline, changed, unaffected, clean) != ("passed", "assertion_failure", "passed", "passed"):
            raise AssertionError("mutation survived or control failed: " + name)
        receipts.append(dict(name=name, source=source, target=list(target), baseline=baseline,
                             positive=changed, unaffected=unaffected, clean=clean))
        print(name, "killed", flush=True)
    for name, value in sources.items():
        if sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != value:
            raise RuntimeError("original Rust input changed during mutation checks")
    summary = dict(classifier_negative_controls=6, killed=len(receipts), survived=0, baseline_passes=len(receipts), clean_passes=len(receipts),
                   unaffected_passes=len(receipts), source_sha256=sources, cases=receipts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, sort_keys=True, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
