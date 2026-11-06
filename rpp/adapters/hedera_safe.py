"""Shared Python HCS policy. The optional Hiero Python transport is experimental.

There is no officially supported Hedera Python SDK. Shipping products should
call the official JavaScript/Rust write boundary; this transport requires opt-in.
No credential files, dotenv loading, arbitrary mirror URLs, or secret logging.
"""
from __future__ import annotations

import atexit
import base64
import functools
import importlib
import json
import os
import re
import sys
import threading
import time
from asyncio import CancelledError
from dataclasses import dataclass
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener


class HederaError(RuntimeError):
    """A sanitized policy, receipt or verification failure."""


class MirrorPending(Exception):
    """Retryable mirror lag or transient read failure."""


# Instance/registry state never contains a Python signing operation. Native
# capsules own references from creation, including interrupted Python transfers.
_SIGNING_OPERATIONS = {}
_SIGNER_LOCK = threading.RLock()
_NATIVE_SIGNER_API = None


def _control_token(error):
    if isinstance(error, SystemExit):
        code = error.code if type(error.code) is int or error.code is None else None
        return SystemExit, code
    for kind in (KeyboardInterrupt, GeneratorExit, CancelledError):
        if isinstance(error, kind):
            return kind, None
    return None, None


def _raise_control(kind, code):
    if kind is SystemExit:
        raise SystemExit(code) from None
    raise kind() from None


def _native_signer_api():
    global _NATIVE_SIGNER_API
    if sys.implementation.name != "cpython":
        raise HederaError("Experimental Python signing requires CPython capsule support")
    if _NATIVE_SIGNER_API is None:
        try:
            native = importlib.import_module("rpp.adapters._hedera_signer_native")
            _NATIVE_SIGNER_API = SimpleNamespace(new=native.new, release=native.release,
                                                closed=native.closed, invoke=native.invoke)
        except (ImportError, AttributeError, OSError, TypeError):
            raise HederaError("CPython capsule support unavailable; local signing refused") from None
    return _NATIVE_SIGNER_API


def _release_capsule(capsule):
    api = globals().get("_NATIVE_SIGNER_API")
    if api is None:  # Late interpreter teardown: normal release already ran via atexit.
        return
    with _SIGNER_LOCK:
        api.release(capsule)  # Native tombstone + release is one ownership operation.


def _invoke_capsule(capsule, payload):
    failed, closed, control, code = False, False, None, None
    try:
        api = _native_signer_api()
        with _SIGNER_LOCK:
            if api.closed(capsule):
                closed = True
                raise HederaError("Hedera signer is closed")
        result = api.invoke(capsule, payload)
    except BaseException as error:  # noqa: BLE001 - discard SDK state and preserve fresh control flow.
        control, code = _control_token(error)
        failed = True
    if failed:
        if control is not None:
            _raise_control(control, code)
        # Raise after leaving the handler: no retained SDK exception or context.
        raise HederaError("Hedera signer is closed" if closed else "Hedera signing failed") from None
    return result


def _close_signers():
    operations, lock = globals().get("_SIGNING_OPERATIONS"), globals().get("_SIGNER_LOCK")
    if operations is None or lock is None or globals().get("_NATIVE_SIGNER_API") is None:
        return
    with lock:
        for capsule in tuple(operations.values()):
            _release_capsule(capsule)
        operations.clear()


atexit.register(_close_signers)


class _Signer:
    """Opaque callable; public/slot state contains only the public key."""

    __slots__ = ("_public_key",)

    def __init__(self, key):
        operation, capsule, failure, control, code = None, None, None, None, None
        try:
            api = _native_signer_api()
            with _SIGNER_LOCK:
                if id(self) in _SIGNING_OPERATIONS:
                    raise TypeError("Hedera signer cannot be reinitialized")
                self._public_key = key.public_key()
                operation = key.sign
                capsule = api.new(operation)  # Owns its callback before returning to Python.
                _SIGNING_OPERATIONS[id(self)] = capsule
        except BaseException as error:  # noqa: BLE001 - discard SDK state and preserve fresh control flow.
            control, code = _control_token(error)
            failure = MemoryError if isinstance(error, MemoryError) else TypeError if isinstance(error, TypeError) else HederaError
        finally:
            key = operation = None  # Clear even unsupported-API, allocation and reinitialization tracebacks.
            if failure is not None and capsule is not None:
                _release_capsule(capsule)
                if _SIGNING_OPERATIONS.get(id(self)) is capsule:
                    _SIGNING_OPERATIONS.pop(id(self), None)
            capsule = None
        if control is not None:
            _raise_control(control, code)
        if failure is not None:
            raise failure("CPython capsule signer initialization failed") from None

    @property
    def public_key(self):
        return self._public_key

    def __call__(self, payload):
        with _SIGNER_LOCK:
            capsule = _SIGNING_OPERATIONS.get(id(self))
            if capsule is None:
                raise HederaError("Hedera signer is closed")
        return _invoke_capsule(capsule, payload)

    def __del__(self):
        operations = globals().get("_SIGNING_OPERATIONS")
        lock = globals().get("_SIGNER_LOCK")
        if operations is not None and lock is not None and globals().get("_NATIVE_SIGNER_API") is not None:
            with lock:
                capsule = operations.get(id(self))
                if capsule is not None:
                    _release_capsule(capsule)
                    operations.pop(id(self), None)  # Release before unpublishing; interrupted cleanup stays discoverable.

    def __repr__(self):
        return "<HederaSigner redacted>"

    def __getstate__(self):
        raise TypeError("Hedera signer state cannot be serialized")

    def __setstate__(self, state):
        raise TypeError("Hedera signer state cannot be restored")

    def __reduce__(self):
        raise TypeError("Hedera signer reduction cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Hedera signer cannot be serialized")

    def __copy__(self):
        raise TypeError("Hedera signer cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("Hedera signer cannot be deep-copied")


class _TestnetRoute:
    """Pin the initialized testnet network object, node identities and endpoints."""

    def __init__(self, client):
        self.network = client.network
        self.nodes = self._nodes(client)
        self.mirror = client.network.mirror_address
        self.validate(client)

    @staticmethod
    def _nodes(client):
        return tuple((id(node), str(node._account_id), str(node._address)) for node in client.network.nodes)

    def validate(self, client):
        if (client.network is not self.network or client.network.network != "testnet" or
                client.network.ledger_id != b"\x01" or self._nodes(client) != self.nodes or
                client.network.mirror_address != self.mirror or
                not client.is_transport_security() or not client.is_verify_certificates()):
            raise HederaError("Initialized testnet routing or TLS configuration changed")


class _SendGuard:
    """One total consensus-send budget; validate immediately before each RPC."""

    def __init__(self, config, original_method, route_check):
        self.config, self.remaining, self.original_method = config, config.attempts, original_method
        self.route_check = route_check

    def method_for(self, channel):
        method = self.original_method(channel)
        method.transaction = functools.partial(self.send, method.transaction)
        return method

    def send(self, rpc, request, timeout):
        self.config.validate()  # Concrete consensus RPC authorization boundary.
        self.route_check()  # Pin actual node routing, not only the SDK network label.
        if self.remaining <= 0:
            raise HederaError("Consensus send budget exhausted")
        self.remaining -= 1
        return rpc(request, timeout=timeout)


def _disable_native_retries(client):
    # Pinned 0.3.0 private hook: preserve TLS options and disable native resends.
    for node in client.network.nodes:
        original = node._build_channel_options
        if getattr(original, "_day1_no_retries", False):
            continue

        def options(base=original):
            return [(key, value) for key, value in base() if key != "grpc.enable_retries"] + [("grpc.enable_retries", 0)]

        options._day1_no_retries = True
        node._build_channel_options = options


@dataclass(frozen=True)
class Config:
    network: str = "testnet"
    fee_tinybars: int = 100_000_000
    attempts: int = 3
    timeout_seconds: int = 10
    mirror_attempts: int = 20
    retry_delay_ms: int = 1000

    @classmethod
    def from_env(cls):
        try:
            result = cls(os.environ.get("HEDERA_NETWORK", "testnet"),
                         int(os.environ.get("HEDERA_MAX_FEE_TINYBARS", "100000000")),
                         int(os.environ.get("HEDERA_MAX_ATTEMPTS", "3")),
                         mirror_attempts=int(os.environ.get("HEDERA_MIRROR_ATTEMPTS", "20")),
                         retry_delay_ms=int(os.environ.get("HEDERA_RETRY_DELAY_MS", "1000")))
        except (ValueError, TypeError):
            raise HederaError("Invalid Hedera configuration") from None
        result.validate()
        return result

    def validate(self):
        if self.network != "testnet" or os.environ.get("HEDERA_NETWORK", "testnet") != "testnet":
            raise HederaError("Only Hedera testnet is permitted")
        if type(self.fee_tinybars) is not int or not 0 < self.fee_tinybars <= 100_000_000:
            raise HederaError("Fee cap must be 1..100000000 tinybars")
        if type(self.attempts) is not int or not 1 <= self.attempts <= 5:
            raise HederaError("Retry attempts must be 1..5")
        if type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 30:
            raise HederaError("Request timeout must be 1..30 seconds")
        if type(self.mirror_attempts) is not int or not 1 <= self.mirror_attempts <= 30:
            raise HederaError("Mirror attempts must be 1..30")
        if type(self.retry_delay_ms) is not int or not 0 <= self.retry_delay_ms <= 5000:
            raise HederaError("Retry delay must be 0..5000 milliseconds")

    @property
    def mirror(self):
        return "https://testnet.mirrornode.hedera.com"


def _topic_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"0\.0\.[1-9][0-9]*", value):
        raise HederaError("Invalid topic ID")
    return value


def _require_no_custom_fees(state, topic):
    fees = state.get("custom_fees") if isinstance(state, dict) else None
    if (not isinstance(state, dict) or state.get("topic_id") != topic or not isinstance(fees, dict) or
            set(fees) - {"created_timestamp", "fixed_fees"} or fees.get("fixed_fees") != [] or
            ("created_timestamp" in fees and (not isinstance(fees["created_timestamp"], str) or
             not re.fullmatch(r"[0-9]+\.[0-9]{9}", fees["created_timestamp"])))):
        raise HederaError("Custom fees must have an explicit readable empty schedule")


def _read_mirror(config, mirror, path, pause=time.sleep):
    for attempt in range(config.mirror_attempts):
        try:
            return mirror.get(path)
        except MirrorPending:
            if attempt + 1 == config.mirror_attempts:
                raise HederaError("Mirror confirmation unavailable; write may have succeeded") from None
            pause(config.retry_delay_ms / 1000)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HederaError("Mirror redirects are refused")


class Mirror:
    def __init__(self, config):
        self.config = config

    def get(self, path):
        # Only internally generated, validated paths reach this boundary.
        try:
            with build_opener(_NoRedirect).open(self.config.mirror + path, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read(1_048_577))
        except HTTPError as error:
            if error.code in {404, 408, 429, 500, 502, 503, 504}:
                raise MirrorPending() from None
            raise HederaError("Mirror HTTP request rejected") from None
        except (URLError, TimeoutError):
            raise MirrorPending() from None
        except (ValueError, OSError):
            raise HederaError("Invalid mirror response") from None


class Session:
    """Policy shared by Python callers; injected backend/mirror support fake tests."""

    def __init__(self, config, backend, mirror=None, pause=time.sleep):
        config.validate()
        self.config, self.backend = config, backend
        self.mirror, self.pause = mirror or Mirror(config), pause

    @classmethod
    def from_env(cls):
        config = Config.from_env()
        return cls(config, ExperimentalHieroBackend(config))

    def _read(self, path):
        return _read_mirror(self.config, self.mirror, path, self.pause)

    @staticmethod
    def _receipt(receipt):
        if receipt.get("status") != 22:  # Hedera SUCCESS, including protobuf int form.
            raise HederaError("Transaction receipt was not SUCCESS")
        return receipt

    def create_topic(self, memo="hedera-day1"):
        self.config.validate()  # Recheck live testnet-only selection at every write.
        if not isinstance(memo, str) or len(memo.encode()) > 100:
            raise HederaError("Topic memo exceeds 100 bytes")
        receipt = self._receipt(self.backend.create_topic(memo, self.config))
        topic = _topic_id(receipt.get("topic_id"))
        state = self._read(f"/api/v1/topics/{topic}")
        if (state.get("topic_id") != topic or state.get("memo") != memo or
                (state.get("submit_key") or {}).get("key") != self.backend.public_key or
                (state.get("admin_key") or {}).get("key") != self.backend.public_key):
            raise HederaError("Mirror topic metadata mismatch")
        match = re.fullmatch(r"(0\.0\.[1-9][0-9]*)@([0-9]+)\.([0-9]{1,9})", receipt.get("transaction_id", ""))
        if not match or match[1] != self.backend.operator_id:
            raise HederaError("Invalid topic creation transaction identity")
        mirror_tx = f"{match[1]}-{match[2]}-{match[3].zfill(9)}"
        transactions = self._read(f"/api/v1/transactions/{mirror_tx}").get("transactions", [])
        if not any(t.get("transaction_id") == mirror_tx and t.get("result") == "SUCCESS"
                   and t.get("entity_id") == topic and t.get("name") == "CONSENSUSCREATETOPIC"
                   for t in transactions):
            raise HederaError("Mirror topic creation transaction mismatch")
        return {**receipt, "mirror_confirmed": True}

    def submit(self, topic, payload):
        self.config.validate()
        topic = _topic_id(topic)
        if not isinstance(payload, bytes) or not 0 < len(payload) <= 1024:
            raise HederaError("HCS payload must be 1..1024 bytes; chunking is disabled")
        state = self._read(f"/api/v1/topics/{topic}")
        _require_no_custom_fees(state, topic)
        # Consensus-enforced zero allowance below also protects fee-schedule races.
        receipt = self._receipt(self.backend.submit(topic, payload, self.config))
        sequence = receipt.get("sequence")
        if type(sequence) is not int or sequence < 1:
            raise HederaError("Invalid receipt sequence")
        observed = self._read(f"/api/v1/topics/{topic}/messages/{sequence}")
        try:
            actual = base64.b64decode(observed["message"], validate=True)
        except (ValueError, KeyError, TypeError):
            raise HederaError("Invalid mirror message encoding") from None
        if (observed.get("sequence_number") != sequence or actual != payload or
                observed.get("topic_id") != topic or observed.get("payer_account_id") != self.backend.operator_id):
            raise HederaError("Mirror message bytes, topic, payer or sequence mismatch")
        return {**receipt, "data": actual, "mirror_confirmed": True}

    def signed_record(self, payload):
        return self.backend.signed_record(payload)

    def close(self):
        self.backend.close()


class ExperimentalHieroBackend:
    """Hiero-hosted community SDK 0.3.0 (Pre-Alpha), explicit opt-in only."""

    def __init__(self, config):
        config.validate()
        if os.environ.get("HEDERA_EXPERIMENTAL_PYTHON_ENABLED") != "true":
            raise HederaError("Python SDK is community Pre-Alpha; experimental opt-in required")
        account = os.environ.get("HEDERA_OPERATOR_ID")
        if not account or not os.environ.get("HEDERA_OPERATOR_KEY"):
            raise HederaError("Runtime HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY are required")
        signer, failed, control, code = None, False, None, None
        try:
            import hiero_sdk_python as sdk
            self.sdk = sdk
            self.mirror = Mirror(config)
            self.client = sdk.Client.for_testnet()
            self.client.logger.set_silent(True)
            self.client.set_transport_security(True).set_verify_certificates(True)
            self.client.set_max_attempts(1)  # No hidden SDK consensus retries.
            self.client.set_grpc_deadline(config.timeout_seconds)
            self.client.set_request_timeout(config.timeout_seconds)
            _disable_native_retries(self.client)
            self.client.set_default_max_query_payment(sdk.Hbar.from_tinybars(config.fee_tinybars))
            signer = _Signer(sdk.PrivateKey.from_string(os.environ["HEDERA_OPERATOR_KEY"]))
            self.client.set_operator_with(sdk.AccountId.from_string(account), signer.public_key, signer)
            self._route = _TestnetRoute(self.client)
            self.operator_id = str(self.client.operator.account_id)
            self.public_key = self.client.operator_public_key.to_string_raw()
        except BaseException as error:  # noqa: BLE001 - discard SDK state and preserve fresh control flow.
            control, code = _control_token(error)
            failed = True
        finally:
            if failed and signer is not None:
                signer.__del__()
            signer = None
        if failed:
            if control is not None:
                _raise_control(control, code)
            raise HederaError("Experimental Python SDK initialization failed") from None

    def _execute(self, transaction, config):
        config.validate()
        try:
            self._route.validate(self.client)
            _disable_native_retries(self.client)
            transaction.transaction_fee = config.fee_tinybars
            transaction.set_max_attempts(1)  # Shared boundary owns the total send budget.
            transaction.freeze_with(self.client).sign_with_operator(self.client)
            transaction._get_method = _SendGuard(config, transaction._get_method,
                                                  lambda: self._route.validate(self.client)).method_for
            for attempt in range(config.attempts):
                try:
                    self._route.validate(self.client)  # Before SDK discovery/channel access, including retries.
                    response = transaction.execute(self.client, timeout=config.timeout_seconds, wait_for_receipt=False)
                    break
                except Exception as error:
                    cause = getattr(error, "last_error", error)
                    if getattr(cause, "status", None) not in {12, 67, 69} or attempt + 1 == config.attempts:
                        raise
                    time.sleep(config.retry_delay_ms / 1000)
            receipt = response.get_receipt(self.client, timeout=config.timeout_seconds, validate_status=True)
            return {"status": int(receipt.status), "transaction_id": str(response.transaction_id),
                    "topic_id": str(receipt.topic_id) if receipt.topic_id else None,
                    "sequence": receipt.topic_sequence_number}
        except Exception:  # noqa: BLE001 - SDK errors may contain secrets; sanitize boundary
            raise HederaError("Hedera submission unconfirmed; reconcile before retrying") from None

    def create_topic(self, memo, config):
        tx = (self.sdk.TopicCreateTransaction().set_memo(memo)
              .set_submit_key(self.client.operator_public_key).set_admin_key(self.client.operator_public_key))
        return self._execute(tx, config)

    def submit(self, topic, payload, config):
        config.validate()
        topic = _topic_id(topic)
        if not isinstance(payload, bytes) or not 0 < len(payload) <= 1024:
            raise HederaError("HCS payload must be 1..1024 bytes; chunking is disabled")
        _require_no_custom_fees(_read_mirror(config, self.mirror, f"/api/v1/topics/{topic}"), topic)
        tx = (self.sdk.TopicMessageSubmitTransaction().set_topic_id(self.sdk.TopicId.from_string(topic))
              .set_message(payload))
        # Nonempty payer allowance: zero HBAR; no token denomination is authorized.
        tx.set_custom_fee_limits([self.sdk.CustomFeeLimit(
            payer_id=self.client.operator.account_id,
            custom_fees=[self.sdk.CustomFixedFee(amount=0, denominating_token_id=None)])])
        return self._execute(tx, config)

    def signed_record(self, payload):
        failed, control, code = False, None, None
        try:
            operator = self.client.operator
            signature = operator.signer(payload)
            operator.public_key.verify(signature, payload)
            record = {"version": 1, "payload_base64": base64.b64encode(payload).decode(),
                      "public_key_der": operator.public_key.to_string_der(),
                      "signature_base64": base64.b64encode(signature).decode()}
            return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        except BaseException as error:  # noqa: BLE001 - discard SDK state and preserve fresh control flow.
            control, code = _control_token(error)
            failed = True
        if failed:
            if control is not None:
                _raise_control(control, code)
            raise HederaError("Record signing failed") from None

    def close(self):
        self.client.close()
