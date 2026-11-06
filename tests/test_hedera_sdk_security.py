"""Actual pinned SDK, synthetic in-memory keys, fake discovery/channel/RPC only.

No socket can connect. Key comparisons reduce to booleans before assertions so a
failing regression/mutation cannot disclose synthetic material through pytest.
"""
import base64
import io
import json
import logging
import pickle
import pprint
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rpp.adapters import hedera_safe as safe


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
