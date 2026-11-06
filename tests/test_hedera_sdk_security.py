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

    def build():
        client = sdk.Client.for_network({"offline.invalid:50212": sdk.AccountId.from_string("0.0.3"),
                                         "second-offline.invalid:50212": sdk.AccountId.from_string("0.0.4")},
                                        network_name="testnet")
        monkeypatch.setattr(sdk.Client, "for_testnet", lambda: client)
        generated = sdk.PrivateKey.generate_ed25519()
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
    tombstoned = safe._native_signer_api().pointer(capsule, None) == 1
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
    cast = Mock(side_effect=AssertionError("Closed native pointer must never be dereferenced"))
    monkeypatch.setattr(safe.ctypes, "cast", cast)
    with pytest.raises(safe.HederaError, match="closed"):
        safe._invoke_capsule(capsule, b"closed")
    cast.assert_not_called()


def test_actual_sdk_double_release_never_unpins_tombstone(actual, monkeypatch):
    signer = actual().client.operator.signer
    capsule = safe._SIGNING_OPERATIONS[id(signer)]
    signer.__del__()
    unpin = Mock(side_effect=AssertionError("Closed native pointer must never be decreferenced"))
    monkeypatch.setattr(safe._native_signer_api(), "unpin", unpin)
    safe._release_capsule(capsule)
    unpin.assert_not_called()


@pytest.mark.parametrize("failure", ["allocation", "store"])
def test_actual_sdk_native_initialization_rollback(actual, monkeypatch, failure):
    probe = actual()
    key = probe.sdk.PrivateKey.generate_ed25519()
    reference = weakref.ref(key)

    def refuse(*args):
        raise MemoryError("Synthetic initialization refusal")

    class RejectStore(dict):
        __setitem__ = refuse

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


@pytest.mark.parametrize("unsupported", ["runtime", "api"])
def test_actual_sdk_native_support_fails_closed(actual, monkeypatch, unsupported):
    probe = actual()
    with monkeypatch.context() as patch:
        patch.setattr(safe, "_NATIVE_SIGNER_API", None)
        if unsupported == "runtime":
            patch.setattr(safe.sys, "implementation", SimpleNamespace(name="unsupported"))
        else:
            patch.setattr(safe.ctypes, "PyDLL", lambda _: SimpleNamespace())
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
