"""Child-only N3 probe: keys/diagnostic text stay in memory; output is boolean/count data."""
import dis
import gc
import json
import os
import resource
import signal
import socket
import sys
import traceback
from pathlib import Path

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

import hiero_sdk_python as sdk

from rpp.adapters import hedera_safe as safe


def forbid(*args, **kwargs):
    raise RuntimeError("Network forbidden in initializer diagnostics")


socket.socket.connect = forbid
algorithm, boundary = sys.argv[1:]
key = sdk.PrivateKey.generate(algorithm)
markers = (key.to_string_raw(), key.to_string_der(), repr(key.to_bytes_raw()))
os.environ.update(HEDERA_OPERATOR_ID="0.0.456", HEDERA_OPERATOR_KEY=key.to_string_der(),
                  HEDERA_EXPERIMENTAL_PYTHON_ENABLED="true", HEDERA_NETWORK="testnet")
product = str(Path(safe.__file__).resolve().parents[1]) + os.sep
entry = safe._Signer.__init__
initializer = entry if hasattr(entry, "__code__") else safe._Signer._initialize
targets = {initializer.__code__}
if boundary == "factory":
    targets.add(safe.ExperimentalHieroBackend.__init__.__code__)


class RefuseStore(dict):
    def __setitem__(self, name, value):
        raise MemoryError("Synthetic store failure")


class StoreThenRefuse(dict):
    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        raise MemoryError("Synthetic post-store failure")


class InterruptStore(dict):
    def __setitem__(self, name, value):
        raise KeyboardInterrupt()


def prepare(scenario):
    safe._close_signers()
    registry = {"normal": dict, "refuse": RefuseStore, "stored": StoreThenRefuse,
                "control": InterruptStore, "reinit": dict}[scenario]()
    safe._SIGNING_OPERATIONS = registry
    if boundary == "factory":
        client = sdk.Client.for_network({"offline.invalid:50212": sdk.AccountId.from_string("0.0.3")},
                                        network_name="testnet")
        sdk.Client.for_testnet = lambda: client
        return lambda: safe.ExperimentalHieroBackend(safe.Config())
    if scenario == "reinit":
        signer = safe._Signer(key)
        return lambda: signer.__init__(key)
    return lambda: safe._Signer(key)


def inspect_error(error):
    diagnostic = traceback.TracebackException.from_exception(error, capture_locals=True)
    pending, seen, leaks, frames = [diagnostic], set(), 0, 0
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        for frame in current.stack:
            if str(Path(frame.filename).resolve()).startswith(product):
                frames += 1
                leaks += sum(any(marker in text for marker in markers)
                             for text in (frame.locals or {}).values())
        pending.extend((current.__context__, current.__cause__))
        pending.extend(current.exceptions or ())
    # Inspect the actual retained traceback too, rather than only its formatted copy.
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        tb = current.__traceback__
        while tb is not None:
            frame = tb.tb_frame
            if str(Path(frame.f_code.co_filename).resolve()).startswith(product):
                forms = (repr(frame.f_locals), json.dumps(frame.f_locals, default=str))
                leaks += sum(any(marker in text for marker in markers) for text in forms)
            tb = tb.tb_next
        pending.extend((current.__context__, current.__cause__))
    return leaks, frames


def run(action, target=None):
    observed, fired, error, result = set(), False, None, None
    saved = []
    live_leaks = 0

    def trace(frame, event, arg):
        nonlocal fired, live_leaks
        if frame.f_code in targets and event == "line":
            # Check the running initializer as well as its escaped diagnostic;
            # native exception replacement must not hide a raw Python local.
            forms = (repr(frame.f_locals), json.dumps(frame.f_locals, default=str))
            live_leaks += sum(any(marker in text for marker in markers) for text in forms)
            position = frame.f_code, frame.f_lineno
            observed.add(position)
            if position == target and not fired:
                fired = True
                saved.extend(value for value in frame.f_locals.values() if type(value).__name__ == "PyCapsule")
                signal.raise_signal(signal.SIGINT)
        return trace

    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        sys.settrace(trace)
        try:
            result = action()
        except BaseException as caught:  # noqa: BLE001 - deliberately retain escaped controls.
            error = caught
    finally:
        sys.settrace(None)
        signal.signal(signal.SIGINT, previous)
    leaks, frames = inspect_error(error) if error is not None else (0, 0)
    interrupted = isinstance(error, KeyboardInterrupt)
    open_handles = sum(not safe._native_signer_api().closed(handle) for handle in saved)
    # Keep the actual exception/traceback alive through cleanup and the second inspection.
    safe._close_signers()
    safe._close_signers()
    if result is not None:
        result.close() if boundary == "factory" else result.__del__()
    gc.collect()
    if error is not None:
        after, _ = inspect_error(error)
        leaks += after
    return observed, fired, interrupted, leaks, frames, open_handles, live_leaks


scenarios = ["normal", "refuse", "stored", "control"]
if boundary == "direct":
    scenarios.append("reinit")
cases, covered, leak_count, failed_signals, product_frames, open_handles = 0, set(), 0, 0, 0, 0
live_leak_count = 0
for scenario in scenarios:
    positions, _, _, leaks, frames, _, live = run(prepare(scenario))
    leak_count += leaks
    product_frames += frames
    live_leak_count += live
    for position in sorted(positions, key=lambda item: (item[0].co_firstlineno, item[1])):
        _, fired, interrupted, leaks, frames, opened, live = run(prepare(scenario), position)
        cases += 1
        covered.add(position)
        failed_signals += not (fired and interrupted)
        leak_count += leaks
        product_frames += frames
        open_handles += opened
        live_leak_count += live
initializer_lines = {line for code, line in covered if code is initializer.__code__}
executable = {line for _, line in dis.findlinestarts(initializer.__code__) if line > initializer.__code__.co_firstlineno}
print(json.dumps({"algorithm": algorithm, "boundary": boundary, "cases": cases,
                  "covered_initializer_lines": len(initializer_lines),
                  "uncovered_initializer_lines": sorted(executable - initializer_lines),
                  "product_frames_checked": product_frames,
                  "failed_signals": failed_signals, "key_leaks": leak_count,
                  "live_local_key_leaks": live_leak_count,
                  "open_escaped_handles": open_handles,
                  "native_entry": not hasattr(entry, "__code__"),
                  "registry_empty": not safe._SIGNING_OPERATIONS}))
