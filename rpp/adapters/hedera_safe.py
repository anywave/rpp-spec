"""Shared Python HCS policy. The optional Hiero Python transport is experimental.

There is no officially supported Hedera Python SDK. Shipping products should
call the official JavaScript/Rust write boundary; this transport requires opt-in.
No credential files, dotenv loading, arbitrary mirror URLs, or secret logging.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener


class HederaError(RuntimeError):
    """A sanitized policy, receipt or verification failure."""


class MirrorPending(Exception):
    """Retryable mirror lag or transient read failure."""


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
        if self.network not in {"testnet", "previewnet", "mainnet"}:
            raise HederaError("Unsupported Hedera network")
        if self.network == "mainnet" and os.environ.get("RADIX_HEDERA_MAINNET_ENABLED") != "true":
            raise HederaError("Mainnet requires RADIX runtime authorization")
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
        host = "mainnet-public" if self.network == "mainnet" else self.network
        return f"https://{host}.mirrornode.hedera.com"


def _topic_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"0\.0\.[1-9][0-9]*", value):
        raise HederaError("Invalid topic ID")
    return value


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
        for attempt in range(self.config.mirror_attempts):
            try:
                return self.mirror.get(path)
            except MirrorPending:
                if attempt + 1 == self.config.mirror_attempts:
                    raise HederaError("Mirror confirmation unavailable; write may have succeeded") from None
                self.pause(self.config.retry_delay_ms / 1000)

    @staticmethod
    def _receipt(receipt):
        if receipt.get("status") != 22:  # Hedera SUCCESS, including protobuf int form.
            raise HederaError("Transaction receipt was not SUCCESS")
        return receipt

    def create_topic(self, memo="hedera-day1"):
        self.config.validate()  # Recheck RADIX flag at every write.
        if not isinstance(memo, str) or len(memo.encode()) > 100:
            raise HederaError("Topic memo exceeds 100 bytes")
        receipt = self._receipt(self.backend.create_topic(memo, self.config))
        topic = _topic_id(receipt.get("topic_id"))
        state = self._read(f"/api/v1/topics/{topic}")
        if (state.get("topic_id") != topic or state.get("memo") != memo or
                (state.get("submit_key") or {}).get("key") != self.backend.public_key):
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
        # A single backend call: ambiguous writes are never rebuilt/resubmitted.
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
        secret = os.environ.get("HEDERA_OPERATOR_KEY")
        if not account or not secret:
            raise HederaError("Runtime HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY are required")
        try:
            import hiero_sdk_python as sdk
            self.sdk = sdk
            self.client = getattr(sdk.Client, "for_" + config.network)()
            self.client.logger.set_silent(True)
            self.client.set_transport_security(True).set_verify_certificates(True)
            self.client.set_max_attempts(config.attempts)
            self.client.set_grpc_deadline(config.timeout_seconds)
            self.client.set_request_timeout(config.timeout_seconds)
            self.client.set_default_max_query_payment(sdk.Hbar.from_tinybars(config.fee_tinybars))
            self.client.set_operator(sdk.AccountId.from_string(account), sdk.PrivateKey.from_string(secret))
            self.operator_id = str(self.client.operator.account_id)
            self.public_key = self.client.operator_public_key.to_string_raw()
        except Exception:  # noqa: BLE001 - SDK errors may contain secrets; sanitize boundary
            raise HederaError("Experimental Python SDK initialization failed") from None
        finally:
            secret = None

    def _execute(self, transaction, config):
        config.validate()
        try:
            transaction.transaction_fee = config.fee_tinybars
            transaction.set_max_attempts(config.attempts)
            transaction.freeze_with(self.client).sign_with_operator(self.client)
            # SDK retries the same frozen transaction identity; no new tx on timeout.
            response = transaction.execute(self.client, timeout=config.timeout_seconds, wait_for_receipt=False)
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
        tx = (self.sdk.TopicMessageSubmitTransaction().set_topic_id(self.sdk.TopicId.from_string(topic))
              .set_message(payload))
        return self._execute(tx, config)

    def signed_record(self, payload):
        try:
            operator = self.client.operator
            signature = operator.signer(payload)
            operator.public_key.verify(signature, payload)
            record = {"version": 1, "payload_base64": base64.b64encode(payload).decode(),
                      "public_key_der": operator.public_key.to_string_der(),
                      "signature_base64": base64.b64encode(signature).decode()}
            return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        except Exception:  # noqa: BLE001 - SDK errors may contain secrets; sanitize boundary
            raise HederaError("Record signing failed") from None

    def close(self):
        self.client.close()
