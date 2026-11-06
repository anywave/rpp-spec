"""Actual pinned SDK, synthetic in-memory keys, fake discovery/channel/RPC only.

No socket can connect. Key comparisons reduce to booleans before assertions so a
failing regression/mutation cannot disclose synthetic material through pytest.
"""
import base64
import copy
import copyreg
import gc
import io
import json
import logging
import pickle
import pprint
import socket
import subprocess
import sys
import threading
import traceback
import types
import weakref
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rpp.adapters import hedera_safe as safe


@pytest.fixture(autouse=True)
def no_native_core_dump():
    try:
        import resource
    except ImportError:  # Platforms without Unix core dumps.
        return
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


@pytest.fixture
def actual(monkeypatch):
    sdk = pytest.importorskip("hiero_sdk_python")
    from hiero_sdk_python.hapi.services import (
        basic_types_pb2,
        response_pb2,
        transaction_contents_pb2,
        transaction_pb2,
        transaction_response_pb2,
    )

    connection_attempts = []

    def forbid_connect(*args, **kwargs):
        connection_attempts.append(True)
        raise RuntimeError("Network forbidden in offline SDK probes")

    monkeypatch.setattr(socket.socket, "connect", forbid_connect)
    monkeypatch.setattr(safe.time, "sleep", lambda _: None)

    def build(algorithm="ed25519"):
        client = sdk.Client.for_network({"offline.invalid:50212": sdk.AccountId.from_string("0.0.3"),
                                         "second-offline.invalid:50212": sdk.AccountId.from_string("0.0.4")},
                                        network_name="testnet")
        monkeypatch.setattr(sdk.Client, "for_testnet", lambda: client)
        generated = sdk.PrivateKey.generate(algorithm)
        raw, der, raw_bytes = generated.to_string_raw(), generated.to_string_der(), generated.to_bytes_raw()
        monkeypatch.setenv("HEDERA_OPERATOR_ID", "0.0.456")
        monkeypatch.setenv("HEDERA_OPERATOR_KEY", der)
        monkeypatch.setenv("HEDERA_EXPERIMENTAL_PYTHON_ENABLED", "true")
        monkeypatch.setenv("HEDERA_NETWORK", "testnet")
        config = safe.Config(retry_delay_ms=0)
        backend = safe.ExperimentalHieroBackend(config)
        probe = SimpleNamespace(sdk=sdk, client=client, config=config, backend=backend,
                                sends=[], bodies=[], requests=[], statuses=[], race=None,
                                connections=connection_attempts,
                                before_send=None, before_channel=None, receipt_status=22)

        def contains_secret(value):
            if isinstance(value, str):
                return raw in value or der in value
            return raw_bytes in value or raw.encode() in value or der.encode() in value

        backend.mirror = SimpleNamespace(get=lambda path: {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": []}})
        probe.session = safe.Session(config, backend, backend.mirror)
        probe.contains_secret = contains_secret  # Closure repr contains no key.

        def send(request, timeout):
            signed = transaction_contents_pb2.SignedTransaction.FromString(request.signedTransactionBytes)
            body = transaction_pb2.TransactionBody.FromString(signed.bodyBytes)
            probe.sends.append(safe.os.environ.get("HEDERA_NETWORK", "testnet") == "testnet")
            probe.bodies.append(body)
            probe.requests.append(request.SerializeToString())
            if probe.before_send:
                probe.before_send()
            if probe.race and body.max_custom_fees:
                # Consensus handler semantics: explicit zero HBAR rejects HBAR;
                # nonempty limit with missing token denomination rejects HTS.
                probe.receipt_status = 382 if probe.race == "hbar" else 383
            status = probe.statuses.pop(0) if probe.statuses else 0
            return transaction_response_pb2.TransactionResponse(nodeTransactionPrecheckCode=status)

        def receipt_rpc(request, timeout):
            result = response_pb2.Response()
            result.transactionGetReceipt.header.nodeTransactionPrecheckCode = 0
            result.transactionGetReceipt.receipt.status = probe.receipt_status
            result.transactionGetReceipt.receipt.topicSequenceNumber = 1
            result.transactionGetReceipt.receipt.topicID.CopyFrom(basic_types_pb2.TopicID(topicNum=123))
            return result

        channel = SimpleNamespace(topic=SimpleNamespace(submitMessage=send, createTopic=send),
                                  crypto=SimpleNamespace(getTransactionReceipts=receipt_rpc))
        probe.channel = channel

        def get_channel():
            if probe.before_channel:
                probe.before_channel()
            return channel

        for node in client.network.nodes:
            monkeypatch.setattr(node, "_get_channel", get_channel)
        original_execute = backend._execute

        def capture(transaction, config):
            probe.transaction = transaction
            return original_execute(transaction, config)

        monkeypatch.setattr(backend, "_execute", capture)
        return probe

    return build


def test_actual_sdk_zero_fee_wire(actual):
    probe = actual()
    assert probe.backend.submit("0.0.123", b"record", probe.config)["status"] == 22
    body = probe.bodies[0]
    assert body.transactionFee == 100_000_000
    assert len(body.max_custom_fees) == 1
    limit = body.max_custom_fees[0]
    assert limit.account_id.accountNum == 456
    assert len(limit.fees) == 1 and limit.fees[0].amount == 0
    assert not limit.fees[0].HasField("denominating_token_id")
    alternatives = [wire for chunk in probe.transaction._transaction_body_bytes.values() for wire in chunk.values()]
    assert len(alternatives) == 2
    for wire in alternatives:
        alternative = type(body).FromString(wire)
        assert alternative.transactionFee == body.transactionFee
        assert alternative.max_custom_fees == body.max_custom_fees
    assert probe.client.max_attempts == 1 and probe.transaction._max_attempts == 1
    assert all(dict(node._build_channel_options())["grpc.enable_retries"] == 0
               for node in probe.client.network.nodes)
    assert probe.transaction.is_signed_by(probe.client.operator_public_key)


@pytest.mark.parametrize("network", ["mainnet", "previewnet", "unknown", "TESTNET"])
def test_actual_sdk_non_testnet_never_constructs_client(actual, monkeypatch, network):
    probe = actual()
    factory = Mock(side_effect=AssertionError("Client construction forbidden"))
    monkeypatch.setattr(probe.sdk.Client, "for_testnet", factory)
    monkeypatch.setenv("RADIX_HEDERA_MAINNET_ENABLED", "true")  # Historical flag cannot enable anything.
    monkeypatch.setenv("HEDERA_NETWORK", network)
    with pytest.raises(safe.HederaError, match="Only Hedera testnet"):
        safe.ExperimentalHieroBackend(safe.Config())
    factory.assert_not_called()


@pytest.mark.parametrize("denomination", ["hbar", "hts-token"])
def test_actual_sdk_fee_schedule_race_refused(actual, denomination):
    probe = actual()
    probe.race = denomination
    mirror = SimpleNamespace(get=lambda path: {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": []}})
    session = safe.Session(probe.config, probe.backend, mirror)
    with pytest.raises(safe.HederaError, match="unconfirmed"):
        session.submit("0.0.123", b"record")
    assert len(probe.sends) == 1
    assert probe.receipt_status in {382, 383}


@pytest.mark.parametrize("boundary", ["direct", "session"])
def test_actual_sdk_revoke_after_signing(actual, monkeypatch, boundary):
    probe = actual()
    original = safe._Signer.__call__

    def revoke(signer, payload):
        signature = original(signer, payload)
        monkeypatch.setenv("HEDERA_NETWORK", "mainnet")
        return signature

    monkeypatch.setattr(safe._Signer, "__call__", revoke)
    with pytest.raises(safe.HederaError):
        (probe.backend.submit("0.0.123", b"record", probe.config) if boundary == "direct"
         else probe.session.submit("0.0.123", b"record"))
    assert probe.sends == []


@pytest.mark.parametrize("boundary", ["direct", "session"])
@pytest.mark.parametrize("changed_network", ["mainnet", "previewnet", "unknown"])
def test_actual_sdk_revoke_at_channel_boundary(actual, monkeypatch, boundary, changed_network):
    probe = actual()
    probe.before_channel = lambda: monkeypatch.setenv("HEDERA_NETWORK", changed_network)
    with pytest.raises(safe.HederaError):
        (probe.backend.submit("0.0.123", b"record", probe.config) if boundary == "direct"
         else probe.session.submit("0.0.123", b"record"))
    assert probe.sends == []


@pytest.mark.parametrize("boundary", ["direct", "session"])
def test_actual_sdk_revoke_after_busy(actual, monkeypatch, boundary):
    probe = actual()
    probe.statuses = [12, 0]
    probe.before_send = lambda: monkeypatch.setenv("HEDERA_NETWORK", "mainnet")
    with pytest.raises(safe.HederaError):
        (probe.backend.submit("0.0.123", b"record", probe.config) if boundary == "direct"
         else probe.session.submit("0.0.123", b"record"))
    assert probe.sends == [True]


def test_actual_sdk_one_retry_budget_frozen_identity(actual):
    probe = actual()
    probe.statuses = [12] * 10
    with pytest.raises(safe.HederaError):
        probe.backend.submit("0.0.123", b"record", probe.config)
    assert len(probe.sends) == probe.config.attempts == 3
    assert len(set(probe.requests)) == 1
    assert probe.client.max_attempts == 1 and probe.transaction._max_attempts == 1


def test_actual_sdk_rpc_guard_budget(actual):
    probe = actual()
    probe.backend.submit("0.0.123", b"record", probe.config)
    method = probe.transaction._get_method(probe.channel)
    request = probe.transaction._make_request()
    method.transaction(request, timeout=1)
    method.transaction(request, timeout=1)
    with pytest.raises(safe.HederaError, match="budget exhausted"):
        method.transaction(request, timeout=1)
    assert len(probe.sends) == 3


def test_actual_sdk_signer_inspection_is_redacted(actual):
    probe = actual()
    probe.backend.submit("0.0.123", b"record", probe.config)
    operator = probe.client.operator
    signer = operator.signer
    targets = [probe.backend, vars(probe.backend), probe.client, vars(probe.client),
               operator, operator._asdict(), signer, signer.__call__, probe.transaction,
               vars(probe.transaction), probe.transaction._signers]
    for target in targets:
        for render in (str, repr, pprint.pformat, lambda x: json.dumps(x, default=str),
                       lambda x: json.dumps(x, default=vars), pickle.dumps):
            try:
                rendered = render(target)
            except (TypeError, ValueError, pickle.PickleError) as error:
                rendered = str(error)
            leaked = probe.contains_secret(rendered)
            assert not leaked, "SDK inspection disclosed a synthetic private key"
        output = io.StringIO()
        logger = logging.Logger("isolated-signer-inspection")  # noqa: LOG001 - isolated log sink; no global handlers
        logger.addHandler(logging.StreamHandler(output))
        logger.warning("%s %r", target, target)
        leaked = probe.contains_secret(output.getvalue())
        assert not leaked, "SDK logging disclosed a synthetic private key"
    assert probe.client.operator_private_key is None and operator.private_key is None
    assert signer is probe.transaction._signers[0][1]
    with pytest.raises(TypeError):
        vars(signer)
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(signer)
    signed = json.loads(probe.backend.signed_record(b"synthetic-record"))
    operator.public_key.verify(base64.b64decode(signed["signature_base64"]), b"synthetic-record")


def test_actual_sdk_creation_admin_and_submit_wire(actual):
    probe = actual()
    assert probe.backend.create_topic("security-probe", probe.config)["status"] == 22
    created = probe.bodies[0].consensusCreateTopic
    expected = probe.client.operator_public_key.to_proto_key()
    assert created.adminKey == expected and created.submitKey == expected


@pytest.mark.parametrize("state", [None, [], {}, {"topic_id": "0.0.123"},
    {"topic_id": "0.0.123", "custom_fees": None},
    {"topic_id": "0.0.123", "custom_fees": []},
    {"topic_id": "0.0.123", "custom_fees": {}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": None}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": {}}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": "unreadable"}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": [], "created_timestamp": None}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": [], "unknown": 1}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": [{"amount": 1}]}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": [{"amount": 0}]}},
    {"topic_id": "0.0.123", "custom_fees": {"fixed_fees": [{"amount": 1, "denominating_token_id": "0.0.9"}]}}])
def test_actual_sdk_custom_fee_preflight_refused_before_rpc(actual, state):
    probe = actual()
    probe.backend.mirror = SimpleNamespace(get=lambda _: state)
    with pytest.raises(safe.HederaError, match="explicit readable empty schedule"):
        probe.backend.submit("0.0.123", b"record", probe.config)
    assert probe.sends == []


def test_actual_sdk_unreadable_fee_schedule_refused_before_rpc(actual):
    probe = actual()
    config = safe.Config(mirror_attempts=1)

    def unavailable(_):
        raise safe.MirrorPending()

    probe.backend.mirror = SimpleNamespace(get=unavailable)
    with pytest.raises(safe.HederaError, match="confirmation unavailable"):
        probe.backend.submit("0.0.123", b"record", config)
    assert probe.sends == []


@pytest.mark.parametrize("phase", ["before", "after-sign", "channel", "retry"])
@pytest.mark.parametrize("change", ["replace-network", "replace-nodes", "label", "ledger", "mirror", "tls"])
def test_actual_sdk_public_routing_change_refused(actual, monkeypatch, phase, change):
    probe = actual()
    # A target replacement with the SAME testnet label/ledger is still refused.
    alternate = probe.sdk.Client.for_network({"node00.swirldslabs.com:443": probe.sdk.AccountId.from_string("0.0.3")},
                                             network_name="testnet").network

    def change_route():
        if change == "replace-network":
            probe.client.network = alternate
        elif change == "replace-nodes":
            probe.client.network.nodes = alternate.nodes
        elif change == "label":
            probe.client.network.network = "mainnet"
        elif change == "ledger":
            probe.client.network.ledger_id = b"\x00"
        elif change == "mirror":
            probe.client.network.mirror_address = "changed.invalid:443"
        else:
            probe.client.set_verify_certificates(False)

    if phase == "before":
        change_route()
    elif phase == "channel":
        probe.before_channel = change_route
    elif phase == "retry":
        probe.statuses = [12, 0]
        probe.before_send = change_route
    else:
        original = safe._Signer.__call__

        def sign_then_change(signer, payload):
            result = original(signer, payload)
            change_route()
            return result

        monkeypatch.setattr(safe._Signer, "__call__", sign_then_change)
    with pytest.raises(safe.HederaError):
        probe.backend.submit("0.0.123", b"record", probe.config)
    assert len(probe.sends) == (1 if phase == "retry" else 0)
    assert probe.connections == []


@pytest.mark.parametrize("protocol", ["getstate", "setstate", "reduce", "reduce_ex", "copy", "deepcopy"])
def test_actual_sdk_signer_explicit_protocol_refusal(actual, protocol):
    signer = actual().client.operator.signer
    actions = {"getstate": signer.__getstate__, "setstate": lambda: signer.__setstate__({}),
               "reduce": signer.__reduce__, "reduce_ex": lambda: signer.__reduce_ex__(5),
               "copy": lambda: copy.copy(signer), "deepcopy": lambda: copy.deepcopy(signer)}
    with pytest.raises(TypeError, match="Hedera signer"):
        actions[protocol]()


def test_actual_sdk_signer_public_protocol_graph(actual):
    probe = actual()
    signer = probe.client.operator.signer
    globals_text = repr(signer.__call__.__func__.__globals__)
    leaked = probe.contains_secret(globals_text)
    assert not leaked, "Retained native operations must not disclose keys through function globals formatting"
    # No send is required to inspect retained SDK signing state. This also makes
    # the raw-operation storage ablation fail a leak assertion before invocation.
    transaction = probe.sdk.TopicCreateTransaction().set_memo("public-signer-probe")
    transaction.freeze_with(probe.client).sign_with_operator(probe.client)
    roots = [probe.backend, probe.client, probe.client.operator, signer, transaction,
             transaction._signers, *safe._SIGNING_OPERATIONS.values()]

    def inspect(value):
        for render in (str, repr, pprint.pformat, lambda x: json.dumps(x, default=str),
                       lambda x: json.dumps(x, default=vars), pickle.dumps):
            try:
                rendered = render(value)
            except Exception as error:  # noqa: BLE001 - inspect refusal text without disclosing it.
                rendered = str(error)
            leaked = probe.contains_secret(rendered)
            assert not leaked, "Public signer protocol graph disclosed synthetic key material"

    def protocol_call(action):
        try:
            result = action()
        except Exception as error:  # noqa: BLE001 - any protocol refusal must itself remain safe.
            result = str(error)
        inspect(result)
        return result

    for target in roots:
        inspect(target)
        protocol_call(lambda value=target: vars(value))
        for name, arguments in (("__getstate__", ()), ("__reduce__", ()), ("__reduce_ex__", (5,))):
            method = getattr(target, name, None)
            if method is not None:
                protocol_call(lambda bound=method, args=arguments: bound(*args))
        protocol_call(lambda value=target: copy.copy(value))
        protocol_call(lambda value=target: copy.deepcopy(value))
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            protocol_call(lambda value=target, p=protocol: pickle.dumps(value, protocol=p))
    for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
        with pytest.raises(TypeError):
            pickle.dumps(signer, protocol=protocol)
        with pytest.raises(TypeError):
            object.__reduce_ex__(signer, protocol)
    with pytest.raises(TypeError):
        object.__reduce__(signer)
    for protocol in (0, 1):
        with pytest.raises(TypeError):
            copyreg._reduce_ex(signer, protocol)
    inspect(object.__getstate__(signer))  # Base fallback can expose only public key state.
    with pytest.raises(TypeError):
        weakref.ref(signer)

    queue, seen, retained = [(signer, 0), (probe.client.operator, 0), (transaction._signers, 0)], set(), []
    queue.extend((capsule, 0) for capsule in safe._SIGNING_OPERATIONS.values())
    while queue:
        value, depth = queue.pop()
        if id(value) in seen or depth > 6 or isinstance(value, types.ModuleType):
            continue
        seen.add(id(value))
        retained.append(value)  # Prevent identity reuse from skipping newly discovered bound methods.
        inspect(value)
        if isinstance(value, dict):
            queue.extend((item, depth + 1) for pair in value.items() for item in pair)
        elif isinstance(value, (tuple, list, set, frozenset)):
            queue.extend((item, depth + 1) for item in value)
        elif isinstance(value, (str, bytes, bytearray, int, float, bool, type(None))):
            continue
        elif isinstance(value, (types.MethodType, types.BuiltinMethodType, types.MethodWrapperType)):
            queue.append((value.__self__, depth + 1))
            if hasattr(value, "__func__"):
                queue.append((value.__func__, depth + 1))
        elif isinstance(value, types.FunctionType):
            inspect(value.__globals__)  # Whole mapping must format safely; do not walk process memory/env.
            queue.extend((item, depth + 1) for item in (value.__defaults__, value.__kwdefaults__))
            queue.extend((cell.cell_contents, depth + 1) for cell in value.__closure__ or ())
        elif isinstance(value, type):
            queue.extend((item.fget if isinstance(item, property) else item, depth + 1)
                         for item in vars(value).values() if isinstance(item, (property, types.FunctionType)))
        else:
            for name in dir(value):
                if name != "__globals__":
                    queue.append((getattr(value, name), depth + 1))
            getter = getattr(value, "__getstate__", None)
            if getter is not None:
                queue.append((protocol_call(getter), depth + 1))
    assert len(seen) > 100
    assert probe.connections == []


def test_actual_sdk_native_signer_lifecycle(actual):
    probe = actual()
    gc.collect()
    baseline = len(safe._SIGNING_OPERATIONS)
    for _ in range(128):
        key = probe.sdk.PrivateKey.generate_ed25519()
        reference = weakref.ref(key)
        signer = safe._Signer(key)
        del key
        alive = reference() is not None
        assert alive, "Native operation lost ownership"
        signature = signer(b"native-lifecycle")
        signer.public_key.verify(signature, b"native-lifecycle")
        del signer
        gc.collect()
        released = reference() is None
        assert released, "Native operation was not released"
    assert len(safe._SIGNING_OPERATIONS) == baseline


def test_actual_sdk_saved_capsule_is_invalidated(actual):
    probe = actual()
    key = probe.sdk.PrivateKey.generate_ed25519()
    reference = weakref.ref(key)
    signer = safe._Signer(key)
    capsule = safe._SIGNING_OPERATIONS[id(signer)]
    del key
    signer.__del__()
    signer.__del__()
    tombstoned = safe._native_signer_api().closed(capsule)
    assert tombstoned, "Saved capsule must be invalidated before any stale invocation"
    safe._release_capsule(capsule)
    released = reference() is None
    assert released, "Repeated close retained the operation"
    with pytest.raises(safe.HederaError, match="closed"):
        signer(b"closed")
    with pytest.raises(safe.HederaError, match="closed"):
        safe._invoke_capsule(capsule, b"closed")


def test_actual_sdk_closed_capsule_never_dereferences(actual, monkeypatch):
    probe = actual()
    signer = probe.client.operator.signer
    capsule = safe._SIGNING_OPERATIONS[id(signer)]
    signer.__del__()
    invoke = Mock(side_effect=AssertionError("Closed native operation must never be invoked"))
    monkeypatch.setattr(safe._native_signer_api(), "invoke", invoke)
    with pytest.raises(safe.HederaError, match="closed"):
        safe._invoke_capsule(capsule, b"closed")
    invoke.assert_not_called()


def test_actual_sdk_double_release_never_unpins_tombstone(actual):
    signer = actual().client.operator.signer
    capsule = safe._SIGNING_OPERATIONS[id(signer)]
    signer.__del__()
    repeated = True
    try:
        safe._release_capsule(capsule)
        safe._native_signer_api().release(capsule)
    except safe.HederaError:
        repeated = False
    assert repeated, "Repeated native release must be safe"
    assert safe._native_signer_api().closed(capsule)
    assert not gc.get_referents(capsule), "Native capsule must not expose its signing operation through GC reflection"


@pytest.mark.parametrize("failure", ["allocation", "store"])
def test_actual_sdk_native_initialization_rollback(actual, monkeypatch, failure):
    probe = actual()
    key = probe.sdk.PrivateKey.generate_ed25519()
    reference = weakref.ref(key)
    saved = []

    def refuse(*args):
        raise MemoryError("Synthetic initialization refusal")

    class RejectStore(dict):
        def __setitem__(self, name, capsule):
            saved.append(capsule)
            refuse()

    with monkeypatch.context() as patch:
        if failure == "allocation":
            patch.setattr(safe._native_signer_api(), "new", refuse)
        else:
            patch.setattr(safe, "_SIGNING_OPERATIONS", RejectStore())
        with pytest.raises(MemoryError):
            safe._Signer(key)
    del key
    gc.collect()
    released = reference() is None
    assert released, "Failed initialization retained native ownership"
    assert all(safe._native_signer_api().closed(capsule) for capsule in saved)


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("point", ["new-result", "before-register", "after-register",
                                    "before-release", "after-release", "after-unpublish"])
def test_actual_sdk_interrupted_ownership(actual, algorithm, point):
    # Actual SIGINT at bytecode/line boundaries; the returned error and saved
    # capsule stay alive while checking release. Only booleans leave the child.
    actual()
    program = '''
import dis, gc, inspect, json, resource, signal, socket, sys, weakref
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
import hiero_sdk_python as sdk
from rpp.adapters import hedera_safe as safe
def forbidden(*args): raise RuntimeError("No network permitted")
socket.socket.connect = forbidden
safe._close_signers()
key = sdk.PrivateKey.generate(ALGORITHM)
reference = weakref.ref(key)
saved, error, signer = None, None, None
initializer = safe._Signer.__init__
finalizer = safe._Signer.__del__
function = initializer if POINT in {"new-result", "before-register", "after-register"} else finalizer
instructions = list(dis.get_instructions(function))
if POINT == "new-result":
    call_start = next(item.offset for item in instructions if item.argval == "new")
    target = next(item.offset for item in instructions if item.offset > call_start and
                  item.opname == "STORE_FAST" and item.argval == "capsule")
    event_kind = "opcode"
elif POINT == "after-unpublish":
    pop_start = next(item.offset for item in instructions if item.argval == "pop")
    target = next(item.offset for item in instructions if item.offset > pop_start and
                  item.opname in {"RETURN_VALUE", "RETURN_CONST"})
    event_kind = "opcode"
else:
    fragments = {"before-register": "_SIGNING_OPERATIONS[id(self)] = capsule",
                 "after-register": "if failure is not None and capsule is not None:",
                 "before-release": "_release_capsule(capsule)",
                 "after-release": "operations.pop(id(self), None)"}
    lines, first = inspect.getsourcelines(function)
    target = first + next(index for index, line in enumerate(lines) if fragments[POINT] in line)
    event_kind = "line"
if function is finalizer:
    signer = safe._Signer(key)
    saved = safe._SIGNING_OPERATIONS[id(signer)]
fired = False
def trace(frame, event, arg):
    global fired
    if frame.f_code is function.__code__:
        frame.f_trace_opcodes = True
        position = frame.f_lasti if event_kind == "opcode" else frame.f_lineno
        if event == event_kind and position == target and not fired:
            fired = True
            signal.raise_signal(signal.SIGINT)
    return trace
old_handler = signal.signal(signal.SIGINT, signal.default_int_handler)
try:
    sys._getframe().f_trace_opcodes = True
    sys.settrace(trace)
    try:
        if function is initializer: safe._Signer(key)
        else: signer.__del__()
    except KeyboardInterrupt as caught:
        error = caught
finally:
    sys.settrace(None)
    signal.signal(signal.SIGINT, old_handler)
key = None
safe._close_signers()
safe._close_signers()
gc.collect()
result = {"interrupted": fired and isinstance(error, KeyboardInterrupt),
          "released": reference() is None, "empty": not safe._SIGNING_OPERATIONS,
          "saved_closed": saved is None or safe._native_signer_api().closed(saved)}
print(json.dumps(result))
'''
    program = "ALGORITHM = " + repr(algorithm) + "\nPOINT = " + repr(point) + "\n" + program
    environment = {name: value for name, value in safe.os.environ.items()
                   if name not in {"HEDERA_OPERATOR_KEY", "HEDERA_OPERATOR_ID"}}
    result = subprocess.run([sys.executable, "-X", "faulthandler", "-c", program],
                            env=environment, capture_output=True, text=True, timeout=20, check=False)
    succeeded = result.returncode == 0 and not result.stderr
    assert succeeded, "Interrupted native ownership child failed"
    assert json.loads(result.stdout) == {"interrupted": True, "released": True,
                                       "empty": True, "saved_closed": True}, "Interrupted callback was retained"


@pytest.mark.parametrize("unsupported", ["runtime", "api"])
def test_actual_sdk_native_support_fails_closed(actual, monkeypatch, unsupported):
    probe = actual()
    with monkeypatch.context() as patch:
        patch.setattr(safe, "_NATIVE_SIGNER_API", None)
        if unsupported == "runtime":
            patch.setattr(safe.sys, "implementation", SimpleNamespace(name="unsupported"))
        else:
            patch.setattr(safe.importlib, "import_module", lambda _: SimpleNamespace())
        with pytest.raises(safe.HederaError, match="CPython capsule"):
            safe._Signer(probe.sdk.PrivateKey.generate_ed25519())


def test_actual_sdk_native_concurrent_close(actual):
    probe = actual()
    entered, release = threading.Event(), threading.Event()
    results = []

    def construct():
        key = probe.sdk.PrivateKey.generate_ed25519()
        operation = key.sign

        def blocked(payload):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Synthetic synchronization timeout")
            return operation(payload)

        key.sign = blocked
        return safe._Signer(key), weakref.ref(key)

    signer, reference = construct()
    capsule, public_key = safe._SIGNING_OPERATIONS[id(signer)], signer.public_key

    def work():
        signature = safe._invoke_capsule(capsule, b"concurrent-close")
        public_key.verify(signature, b"concurrent-close")
        results.append(True)

    worker = threading.Thread(target=work)
    worker.start()
    try:
        assert entered.wait(5)
        signer.__del__()
        alive = reference() is not None
        assert alive, "Concurrent close freed an active operation"
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive() and results == [True]
    del signer
    gc.collect()
    released = reference() is None
    assert released, "Completed operation retained ownership"


def test_actual_sdk_native_atexit_cleanup(actual):
    # Runtime-generated keys stay inside the child process; only booleans leave.
    program = '''
import atexit, gc, json, weakref
references = []
def observe():
    gc.collect()
    print(json.dumps({"released": all(ref() is None for ref in references),
                      "remaining": len(safe._SIGNING_OPERATIONS)}))
atexit.register(observe)
import hiero_sdk_python as sdk
from rpp.adapters import hedera_safe as safe
signers = []
for index in range(32):
    key = sdk.PrivateKey.generate_ed25519()
    references.append(weakref.ref(key))
    signers.append(safe._Signer(key))
    del key
'''
    environment = {name: value for name, value in safe.os.environ.items()
                   if name not in {"HEDERA_OPERATOR_KEY", "HEDERA_OPERATOR_ID"}}
    result = subprocess.run([sys.executable, "-X", "faulthandler", "-c", program],
                            env=environment, capture_output=True, text=True, timeout=20, check=False)
    succeeded = result.returncode == 0 and not result.stderr
    assert succeeded, "Native signer interpreter cleanup failed"
    outcome = json.loads(result.stdout)
    assert outcome == {"released": True, "remaining": 0}


def _capture_public_error(action):
    # Catch before returning to test frames containing input credentials/oracles.
    try:
        action()
    except BaseException as error:  # noqa: BLE001 - rich diagnostics include cancellation paths.
        diagnostic = traceback.TracebackException.from_exception(error, capture_locals=True)
        return error, diagnostic
    raise AssertionError("Expected a public diagnostic refusal")


def _assert_public_error_safe(probe, error, diagnostic):
    def state(value):
        if isinstance(value, traceback.FrameSummary):
            return {"filename": value.filename, "name": value.name, "locals": value.locals}
        if isinstance(value, type):
            return value.__name__
        return vars(value)

    pending, seen = [diagnostic], set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        forms = ["".join(current.format()), json.dumps(vars(current), default=state)]
        for frame in current.stack:
            forms.append(json.dumps(frame.locals))
        for rendered in forms:
            leaked = probe.contains_secret(rendered)
            assert not leaked, "Public rich exception diagnostics disclosed synthetic key material"
        pending.extend((current.__context__, current.__cause__))
        pending.extend(current.exceptions or ())
    for rendered in (str(error), repr(error), repr(error.args), json.dumps(vars(error), default=str)):
        leaked = probe.contains_secret(rendered)
        assert not leaked, "Public exception fields disclosed synthetic key material"
    unlinked = error.__context__ is None and error.__cause__ is None
    assert unlinked, "Sanitized failures must not retain underlying SDK contexts"


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("boundary", ["signer", "record", "native"])
@pytest.mark.parametrize("payload", [None, "invalid", object()])
def test_actual_sdk_invalid_payload_rich_diagnostics(actual, algorithm, boundary, payload):
    probe = actual(algorithm)
    operation = probe.client.operator.signer if boundary == "signer" else probe.backend.signed_record
    if boundary == "native":
        capsule = safe._SIGNING_OPERATIONS[id(probe.client.operator.signer)]
        operation = lambda payload: safe._native_signer_api().invoke(capsule, payload)
    error, diagnostic = _capture_public_error(lambda: operation(payload))
    category_ok = isinstance(error, RuntimeError if boundary == "native" else safe.HederaError)
    assert category_ok, "Unexpected sanitized failure category"
    _assert_public_error_safe(probe, error, diagnostic)


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("boundary", ["signer", "record", "native"])
@pytest.mark.parametrize("failure", ["ordinary", "keyboard", "system-int", "system-none", "system-secret", "generator", "cancel"])
def test_actual_sdk_callback_failure_rich_diagnostics(actual, monkeypatch, algorithm, boundary, failure):
    sdk = pytest.importorskip("hiero_sdk_python")

    def refuse(key, payload):
        if failure == "ordinary":
            raise ValueError(key.to_string_raw())
        if failure == "keyboard":
            raise KeyboardInterrupt(key.to_string_raw())
        if failure == "system-int":
            raise SystemExit(7)
        if failure == "system-none":
            raise SystemExit(None)
        if failure == "system-secret":
            raise SystemExit(key.to_string_raw())
        if failure == "generator":
            raise GeneratorExit(key.to_string_raw())
        raise safe.CancelledError(key.to_string_raw())

    monkeypatch.setattr(sdk.PrivateKey, "sign", refuse)
    probe = actual(algorithm)
    operation = probe.client.operator.signer if boundary == "signer" else probe.backend.signed_record
    if boundary == "native":
        capsule = safe._SIGNING_OPERATIONS[id(probe.client.operator.signer)]
        operation = lambda payload: safe._native_signer_api().invoke(capsule, payload)
    error, diagnostic = _capture_public_error(lambda: operation(b"valid-sdk-input"))
    expected = {"ordinary": safe.HederaError, "keyboard": KeyboardInterrupt,
                "system-int": SystemExit, "system-none": SystemExit, "system-secret": SystemExit,
                "generator": GeneratorExit, "cancel": safe.CancelledError}[failure]
    if boundary == "native" and failure == "ordinary":
        expected = RuntimeError
    category_ok = isinstance(error, expected)
    assert category_ok, "Unexpected sanitized failure category"
    if isinstance(error, SystemExit):
        exit_code_ok = error.code == (7 if failure == "system-int" else None)
        assert exit_code_ok, "Control flow retained an unsafe or changed exit code"
    _assert_public_error_safe(probe, error, diagnostic)


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("failure", ["missing-id", "bad-key", "bad-account", "api", "allocation", "store", "post-operator"])
def test_actual_sdk_backend_init_rich_diagnostics(actual, monkeypatch, algorithm, failure):
    probe = actual(algorithm)
    client = probe.sdk.Client.for_network({"offline-init.invalid:50212": probe.sdk.AccountId.from_string("0.0.3")},
                                         network_name="testnet")
    monkeypatch.setattr(probe.sdk.Client, "for_testnet", lambda: client)
    gc.collect()
    baseline = len(safe._SIGNING_OPERATIONS)

    def refuse(*args):
        raise MemoryError("Synthetic initialization failure")

    class RejectStore(dict):
        __setitem__ = refuse

    with monkeypatch.context() as patch:
        if failure == "missing-id":
            patch.delenv("HEDERA_OPERATOR_ID")
        elif failure == "bad-key":
            patch.setenv("HEDERA_OPERATOR_KEY", safe.os.environ["HEDERA_OPERATOR_KEY"] + "invalid")
        elif failure == "bad-account":
            patch.setenv("HEDERA_OPERATOR_ID", "invalid")
        elif failure == "api":
            patch.setattr(safe, "_NATIVE_SIGNER_API", None)
            patch.setattr(safe.importlib, "import_module", lambda _: SimpleNamespace())
        elif failure == "allocation":
            patch.setattr(safe._native_signer_api(), "new", refuse)
        elif failure == "store":
            patch.setattr(safe, "_SIGNING_OPERATIONS", RejectStore())
        else:
            patch.setattr(safe, "_TestnetRoute", refuse)
        error, diagnostic = _capture_public_error(lambda: safe.ExperimentalHieroBackend(safe.Config()))
    category_ok = isinstance(error, safe.HederaError)
    assert category_ok, "Unexpected sanitized failure category"
    _assert_public_error_safe(probe, error, diagnostic)
    assert len(safe._SIGNING_OPERATIONS) == baseline  # Keep the error and its frames alive while checking release.


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("failure", ["api", "allocation", "store", "reinit"])
def test_actual_sdk_direct_init_rich_diagnostics(actual, monkeypatch, algorithm, failure):
    probe = actual(algorithm)

    def refuse(*args):
        raise MemoryError("Synthetic initialization failure")

    class RejectStore(dict):
        __setitem__ = refuse

    with monkeypatch.context() as patch:
        operation = lambda: safe._Signer(probe.sdk.PrivateKey.from_string(safe.os.environ["HEDERA_OPERATOR_KEY"]))
        if failure == "api":
            patch.setattr(safe, "_NATIVE_SIGNER_API", None)
            patch.setattr(safe.importlib, "import_module", lambda _: SimpleNamespace())
        elif failure == "allocation":
            patch.setattr(safe._native_signer_api(), "new", refuse)
        elif failure == "store":
            patch.setattr(safe, "_SIGNING_OPERATIONS", RejectStore())
        else:
            signer = probe.client.operator.signer
            operation = lambda: signer.__init__(probe.sdk.PrivateKey.from_string(safe.os.environ["HEDERA_OPERATOR_KEY"]))
        error, diagnostic = _capture_public_error(operation)
    expected = safe.HederaError if failure == "api" else TypeError if failure == "reinit" else MemoryError
    category_ok = isinstance(error, expected)
    assert category_ok, "Unexpected sanitized failure category"
    _assert_public_error_safe(probe, error, diagnostic)


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
@pytest.mark.parametrize("boundary", ["signer", "backend"])
@pytest.mark.parametrize("failure", ["ordinary", "keyboard", "system-int", "system-none", "system-secret", "generator", "cancel"])
def test_actual_sdk_key_derivation_failure_rich_diagnostics(actual, monkeypatch, algorithm, boundary, failure):
    probe = actual(algorithm)

    def refuse(key):
        if failure == "ordinary":
            raise ValueError(key.to_string_raw())
        if failure == "keyboard":
            raise KeyboardInterrupt(key.to_string_raw())
        if failure == "system-int":
            raise SystemExit(7)
        if failure == "system-none":
            raise SystemExit(None)
        if failure == "system-secret":
            raise SystemExit(key.to_string_raw())
        if failure == "generator":
            raise GeneratorExit(key.to_string_raw())
        raise safe.CancelledError(key.to_string_raw())

    monkeypatch.setattr(probe.sdk.PrivateKey, "public_key", refuse)
    operation = (lambda: safe._Signer(probe.sdk.PrivateKey.from_string(safe.os.environ["HEDERA_OPERATOR_KEY"])))
    if boundary == "backend":
        operation = lambda: safe.ExperimentalHieroBackend(safe.Config())
    error, diagnostic = _capture_public_error(operation)
    expected = {"ordinary": safe.HederaError, "keyboard": KeyboardInterrupt,
                "system-int": SystemExit, "system-none": SystemExit, "system-secret": SystemExit,
                "generator": GeneratorExit, "cancel": safe.CancelledError}[failure]
    category_ok = isinstance(error, expected)
    assert category_ok, "Unexpected sanitized failure category"
    if isinstance(error, SystemExit):
        exit_code_ok = error.code == (7 if failure == "system-int" else None)
        assert exit_code_ok, "Control flow retained an unsafe or changed exit code"
    _assert_public_error_safe(probe, error, diagnostic)


@pytest.mark.parametrize("algorithm", ["ed25519", "ecdsa"])
def test_actual_sdk_real_interrupt_rich_diagnostics(actual, algorithm):
    program = '''
import json, resource, signal, socket, traceback
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
import hiero_sdk_python as sdk
from rpp.adapters import hedera_safe as safe
def forbidden(*args): raise RuntimeError("No network permitted")
socket.socket.connect = forbidden
key = sdk.PrivateKey.generate(ALGORITHM)
markers = (key.to_string_raw(), key.to_string_der())
signer = safe._Signer(key)
def interrupt(signum, frame): raise KeyboardInterrupt()
def capture():
    previous = signal.signal(signal.SIGALRM, interrupt)
    try:
        signal.setitimer(signal.ITIMER_REAL, 0.0001)
        try: signer(b"A" * 1048576)
        except BaseException as error:  # noqa: BLE001 - rich diagnostics include cancellation paths.
            signal.setitimer(signal.ITIMER_REAL, 0)
            return type(error).__name__, traceback.TracebackException.from_exception(error, capture_locals=True)
        raise AssertionError("Signing was not interrupted")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
kind, diagnostic = capture()
leaked = any(marker in "".join(diagnostic.format()) for marker in markers)
current = diagnostic
while current is not None:
    leaked = leaked or any(marker in value for frame in current.stack
        for value in (frame.locals or {}).values() for marker in markers)
    current = current.__context__
print(json.dumps({"kind": kind, "leaked": leaked, "context": diagnostic.__context__ is not None}))
'''.replace("ALGORITHM", repr(algorithm))
    environment = {name: value for name, value in safe.os.environ.items()
                   if name not in {"HEDERA_OPERATOR_KEY", "HEDERA_OPERATOR_ID"}}
    result = subprocess.run([sys.executable, "-X", "faulthandler", "-c", program], env=environment,
                            capture_output=True, text=True, timeout=20, check=False)
    succeeded = result.returncode == 0 and not result.stderr
    assert succeeded, "Interrupted signing diagnostic probe failed"
    assert json.loads(result.stdout) == {"kind": "KeyboardInterrupt", "leaked": False, "context": False}
