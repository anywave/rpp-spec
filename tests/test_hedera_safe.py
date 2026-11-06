"""Guard tests use fake transports; no operator keys or real network calls."""
import base64
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rpp.adapters.hedera import HederaTransport
from rpp.adapters.hedera_safe import (
    Config,
    ExperimentalHieroBackend,
    HederaError,
    MirrorPending,
    Session,
)


class FakeBackend:
    public_key = "fake-public-identifier"
    operator_id = "0.0.456"

    def create_topic(self, memo, config):
        return {"status": 22, "topic_id": "0.0.123", "transaction_id": "0.0.456@1.000000001"}

    def submit(self, topic, payload, config):
        return {"status": 22, "sequence": 1, "transaction_id": "fake-submit"}

    def close(self):
        pass


@pytest.fixture
def session():
    mirror = Mock()
    mirror.get.return_value = {"topic_id": "0.0.123", "memo": "hedera-day1",
                               "submit_key": {"key": FakeBackend.public_key},
                               "payer_account_id": "0.0.456", "sequence_number": 1, "message": base64.b64encode(b"record").decode()}
    original = mirror.get.return_value
    def respond(path):
        if path.startswith("/api/v1/transactions/"):
            return {"transactions": [{"transaction_id": "0.0.456-1-000000001", "result": "SUCCESS",
                                      "entity_id": "0.0.123", "name": "CONSENSUSCREATETOPIC"}]}
        return original
    mirror.get.side_effect = respond
    return Session(Config(), FakeBackend(), mirror, pause=lambda _: None)


def test_default_testnet(monkeypatch):
    monkeypatch.delenv("HEDERA_NETWORK", raising=False)
    assert Config.from_env().network == "testnet"
    assert Config().mirror == "https://testnet.mirrornode.hedera.com"


def test_mainnet_guard(monkeypatch):
    monkeypatch.delenv("RADIX_HEDERA_MAINNET_ENABLED", raising=False)
    with pytest.raises(HederaError, match="RADIX"):
        Session(Config(network="mainnet"), FakeBackend())
    monkeypatch.setenv("RADIX_HEDERA_MAINNET_ENABLED", "TRUE")
    with pytest.raises(HederaError):
        Config(network="mainnet").validate()


def test_runtime_mainnet_revocation(monkeypatch, session):
    monkeypatch.setenv("RADIX_HEDERA_MAINNET_ENABLED", "true")
    session.config = Config(network="mainnet")
    monkeypatch.delenv("RADIX_HEDERA_MAINNET_ENABLED")
    with pytest.raises(HederaError, match="RADIX"):
        session.submit("0.0.123", b"record")
    with pytest.raises(HederaError, match="RADIX"):
        session.create_topic()


@pytest.mark.parametrize("fields", [{"network": "mispelled"}, {"fee_tinybars": 0},
    {"fee_tinybars": 100_000_001}, {"fee_tinybars": True}, {"attempts": 0},
    {"attempts": 6}, {"timeout_seconds": 0}, {"timeout_seconds": 31}])
def test_invalid_config(fields):
    with pytest.raises(HederaError):
        Config(**fields).validate()


def test_experimental_gate_and_env_only(monkeypatch):
    monkeypatch.delenv("HEDERA_EXPERIMENTAL_PYTHON_ENABLED", raising=False)
    with pytest.raises(HederaError, match="experimental opt-in"):
        ExperimentalHieroBackend(Config())
    monkeypatch.setenv("HEDERA_EXPERIMENTAL_PYTHON_ENABLED", "true")
    monkeypatch.delenv("HEDERA_OPERATOR_KEY", raising=False)
    monkeypatch.delenv("HEDERA_OPERATOR_ID", raising=False)
    with pytest.raises(HederaError, match="Runtime"):
        ExperimentalHieroBackend(Config())
    # Object sentinels are not credentials; even mock callers cannot inject them.
    with pytest.raises(ValueError, match="runtime environment"):
        HederaTransport(operator_key=object())


def test_topic_readback(session):
    assert session.create_topic()["mirror_confirmed"]
    assert session.mirror.get.call_args_list[0].args == ("/api/v1/topics/0.0.123",)
    assert session.mirror.get.call_count == 2


@pytest.mark.parametrize("field,value", [("topic_id", "0.0.999"), ("memo", "different"),
                                        ("submit_key", {"key": "different"})])
def test_topic_mismatch(session, field, value):
    session.mirror.get.return_value[field] = value
    with pytest.raises(HederaError, match="metadata mismatch"):
        session.create_topic()


def test_submit_bytes(session):
    assert session.submit("0.0.123", b"record")["data"] == b"record"
    session.mirror.get.assert_called_once_with("/api/v1/topics/0.0.123/messages/1")


@pytest.mark.parametrize("changes", [{"message": base64.b64encode(b"tampered").decode()},
                                   {"sequence_number": 2}, {"topic_id": "0.0.321"},
                                   {"payer_account_id": "0.0.999"}, {"message": "%%%"}])
def test_message_mismatch(session, changes):
    session.mirror.get.return_value.update(changes)
    with pytest.raises(HederaError):
        session.submit("0.0.123", b"record")


@pytest.mark.parametrize("operation", ["create_topic", "submit"])
def test_receipt_failure(session, operation):
    setattr(session.backend, operation, Mock(return_value={"status": 23, "topic_id": "0.0.123", "sequence": 1}))
    with pytest.raises(HederaError, match="SUCCESS"):
        session.create_topic() if operation == "create_topic" else session.submit("0.0.123", b"record")
    session.mirror.get.assert_not_called()


def test_mirror_retry_bound(session):
    session.mirror.get.side_effect = MirrorPending()
    with pytest.raises(HederaError, match="may have succeeded"):
        session.submit("0.0.123", b"record")
    assert session.mirror.get.call_count == 20


def test_mirror_eventual_consistency_no_resubmit(session):
    session.backend.submit = Mock(wraps=session.backend.submit)
    result = session.mirror.get.return_value
    session.mirror.get.side_effect = [MirrorPending(), result]
    assert session.submit("0.0.123", b"record")["mirror_confirmed"]
    session.backend.submit.assert_called_once()
    assert session.mirror.get.call_count == 2


def test_ambiguous_write_never_resubmitted(session):
    session.backend.submit = Mock(side_effect=HederaError("Unconfirmed"))
    with pytest.raises(HederaError):
        session.submit("0.0.123", b"record")
    session.backend.submit.assert_called_once()
    session.mirror.get.assert_not_called()


@pytest.mark.parametrize("topic,payload", [("0.0.0", b"x"), ("../../x", b"x"),
    ("0.0.123", b""), ("0.0.123", b"x" * 1025)])
def test_input_limits(session, topic, payload):
    with pytest.raises(HederaError):
        session.submit(topic, payload)


def test_sdk_transaction_policy():
    # Contract fake exposes SDK method names; no signing material is created.
    backend = object.__new__(ExperimentalHieroBackend)
    backend.client = object()
    receipt = SimpleNamespace(status=22, topic_id=None, topic_sequence_number=1)
    response = Mock(transaction_id="fake-transaction")
    response.get_receipt.return_value = receipt
    transaction = Mock()
    transaction.freeze_with.return_value = transaction
    transaction.sign_with_operator.return_value = transaction
    transaction.execute.return_value = response
    assert backend._execute(transaction, Config())["status"] == 22
    assert transaction.transaction_fee == 100_000_000
    transaction.set_max_attempts.assert_called_once_with(3)
    transaction.freeze_with.assert_called_once_with(backend.client)
    transaction.sign_with_operator.assert_called_once_with(backend.client)
    transaction.execute.assert_called_once_with(backend.client, timeout=10, wait_for_receipt=False)
    response.get_receipt.assert_called_once_with(backend.client, timeout=10, validate_status=True)


def test_sdk_error_redaction():
    backend = object.__new__(ExperimentalHieroBackend)
    backend.client = object()
    transaction = Mock()
    transaction.freeze_with.side_effect = ValueError("sensitive runtime marker")
    with pytest.raises(HederaError) as error:
        backend._execute(transaction, Config())
    assert "sensitive runtime marker" not in str(error.value)
    assert error.value.__suppress_context__


def test_rpp_mock_preserved():
    transport = HederaTransport()
    assert transport.publish(2 << 17, b"record")["sequence"] == 1
    assert transport.subscribe(2)[0]["data"] == b"record"


def test_sdk_release_api_offline():
    sdk = pytest.importorskip("hiero_sdk_python")
    from importlib.metadata import version
    assert version("hiero-sdk-python") == "0.3.0"
    tx = sdk.TopicMessageSubmitTransaction().set_topic_id(sdk.TopicId.from_string("0.0.123"))
    tx.set_message(b"record").set_max_attempts(3)
    tx.transaction_fee = 100_000_000
    assert tx.transaction_fee == 100_000_000
    assert tx.get_required_chunks() == 1
    assert callable(sdk.Client.set_transport_security)
    assert callable(sdk.Client.set_verify_certificates)
    assert callable(sdk.TransactionResponse.get_receipt)


def test_create_transaction_mismatch(session):
    state = session.mirror.get.return_value
    session.mirror.get.side_effect = [state, {"transactions": []}]
    with pytest.raises(HederaError, match="creation transaction mismatch"):
        session.create_topic()


def test_no_redirects():
    from rpp.adapters.hedera_safe import _NoRedirect
    with pytest.raises(HederaError, match="redirects"):
        _NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://example.invalid")


def test_smoke_requires_throwaway_before_client(monkeypatch, capsys):
    import runpy
    from pathlib import Path
    script = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/hedera_python_smoke.py"))
    monkeypatch.setenv("HEDERA_NETWORK", "testnet")
    monkeypatch.delenv("HEDERA_TESTNET_THROWAWAY", raising=False)
    construct = Mock(side_effect=AssertionError("No client permitted"))
    monkeypatch.setattr(Session, "from_env", construct)
    assert script["main"]() == 2
    assert "attestation" in capsys.readouterr().out
    construct.assert_not_called()
