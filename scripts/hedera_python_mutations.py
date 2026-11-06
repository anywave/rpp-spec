"""Run named assertion tests against isolated compilable safety-rule deletions."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("testnet-default", 'network: str = "testnet"', 'network: str = "previewnet"', "test_default_testnet"),
    ("testnet-only", 'if self.network != "testnet" or os.environ.get("HEDERA_NETWORK", "testnet") != "testnet":', 'if False:', "test_mainnet_guard"),
    ("environment-only", 'if operator_account is not None or operator_key is not None:', 'if False:', "test_experimental_gate_and_env_only"),
    ("experimental-gate", 'if os.environ.get("HEDERA_EXPERIMENTAL_PYTHON_ENABLED") != "true":', 'if False:', "test_experimental_gate_and_env_only"),
    ("fee-cap", 'transaction.transaction_fee = config.fee_tinybars', 'pass', "test_sdk_transaction_policy"),
    ("bounded-sdk-retry", 'transaction.set_max_attempts(1)', 'transaction.set_max_attempts(config.attempts)', "test_actual_sdk_one_retry_budget_frozen_identity"),
    ("client-sdk-retry", 'self.client.set_max_attempts(1)', 'self.client.set_max_attempts(config.attempts)', "test_actual_sdk_zero_fee_wire"),
    ("native-grpc-retry", '[("grpc.enable_retries", 0)]', '[("grpc.enable_retries", 1)]', "test_actual_sdk_zero_fee_wire"),
    ("signed-transaction", '.sign_with_operator(self.client)', '', "test_sdk_transaction_policy"),
    ("receipt-success", 'if receipt.get("status") != 22:', 'if False:', "test_receipt_failure"),
    ("topic-readback", 'state.get("memo") != memo', 'False', "test_topic_mismatch"),
    ("create-tx-readback", 'if not any(t.get("transaction_id")', 'if False and not any(t.get("transaction_id")', "test_create_transaction_mismatch"),
    ("message-bytes", 'actual != payload', 'False', "test_message_mismatch"),
    ("message-topic", 'observed.get("topic_id") != topic', 'False', "test_message_mismatch"),
    ("message-payer", 'observed.get("payer_account_id") != self.backend.operator_id', 'False', "test_message_mismatch"),
    ("mirror-retry", 'range(config.mirror_attempts)', 'range(1)', "test_mirror_retry_bound"),
    ("custom-fee-preflight", 'fees.get("fixed_fees") != []', 'False', "test_actual_sdk_custom_fee_preflight_refused_before_rpc"),
    ("custom-fee-wire", 'tx.set_custom_fee_limits([self.sdk.CustomFeeLimit(\n            payer_id=self.client.operator.account_id,\n            custom_fees=[self.sdk.CustomFixedFee(amount=0, denominating_token_id=None)])])', 'tx.set_custom_fee_limits([])', "test_actual_sdk_zero_fee_wire"),
    ("concrete-send-authorization", 'self.config.validate()  # Concrete consensus RPC authorization boundary.', 'pass  # Authorization removed', "test_actual_sdk_revoke_at_channel_boundary"),
    ("concrete-route-pin", 'self.route_check()  # Pin actual node routing, not only the SDK network label.', 'pass  # Route pin removed', "test_actual_sdk_public_routing_change_refused"),
    ("concrete-send-budget", 'if self.remaining <= 0:', 'if False:', "test_actual_sdk_rpc_guard_budget"),
    ("native-public-key-handoff", 'PyObject_CallMethod(self, "_initialize", "OO", public_key, capsule)', 'PyObject_CallMethod(self, "_initialize", "OO", key, capsule)', "test_actual_sdk_native_initializer_public_handoff"),
    ("native-initializer-boundary", '_Signer.__init__ = _native_signer_api().initializer(_Signer)',
     'def unsafe_initializer(self, key):\n        operation = None\n        try:\n            operation = key.sign\n            self._initialize(key.public_key(), _native_signer_api().new(operation))\n        finally:\n            key = operation = None\n    _Signer.__init__ = unsafe_initializer', "test_actual_sdk_initializer_sigint_locals"),
    ("state-get-refusal", 'raise TypeError("Hedera signer state cannot be serialized")', 'return {}', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("state-set-refusal", 'raise TypeError("Hedera signer state cannot be restored")', 'return None', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("reduce-refusal", 'raise TypeError("Hedera signer reduction cannot be serialized")', 'return None', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("reduce-ex-refusal", 'raise TypeError("Hedera signer cannot be serialized")', 'return None', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("copy-refusal", 'raise TypeError("Hedera signer cannot be copied")', 'return self', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("deepcopy-refusal", 'raise TypeError("Hedera signer cannot be deep-copied")', 'return self', "test_actual_sdk_signer_explicit_protocol_refusal"),
    ("closed-native-invoke", 'if api.closed(capsule):', 'if False:', "test_actual_sdk_closed_capsule_never_dereferences"),
    ("native-close-idempotence", 'api.release(capsule)  # Native tombstone + release is one ownership operation.', 'if api.closed(capsule):\n            raise HederaError("Repeated close refused")\n        api.release(capsule)', "test_actual_sdk_double_release_never_unpins_tombstone"),
    ("native-release", 'api.release(capsule)  # Native tombstone + release is one ownership operation.', 'pass', "test_actual_sdk_saved_capsule_is_invalidated"),
    ("native-automatic-owner", 'PyCapsule_New(operation, signer_name, signer_destructor)', 'PyCapsule_New(operation, signer_name, NULL)', "test_actual_sdk_interrupted_ownership"),
    ("native-initializer-rollback", 'signer_destructor(capsule);', ';', "test_actual_sdk_initializer_sigint_locals"),
    ("native-initializer-operation-release", 'Py_CLEAR(operation);', ';', "test_actual_sdk_native_signer_lifecycle"),
    ("native-cpython-only", 'if sys.implementation.name != "cpython":', 'if False:', "test_actual_sdk_native_support_fails_closed"),
    ("native-owner-cleanup", 'if capsule is not None:\n                    _release_capsule(capsule)', 'if capsule is not None:\n                    pass', "test_actual_sdk_saved_capsule_is_invalidated"),
    ("native-exit-cleanup", 'atexit.register(_close_signers)', 'pass', "test_actual_sdk_native_atexit_cleanup"),
    ("native-unpublish-order", 'capsule = operations.get(id(self))', 'capsule = operations.pop(id(self), None)', "test_actual_sdk_interrupted_ownership"),
    ("callback-context-discard", '        failed = True\n    if failed:', '        failed = True\n        raise HederaError("Unsafe SDK context") from None\n    if failed:', "test_actual_sdk_invalid_payload_rich_diagnostics"),
    ("native-error-redaction", 'sanitize_error(0);', ';', "test_actual_sdk_callback_failure_rich_diagnostics"),
    ("native-initializer-error-redaction", 'if (result == NULL) {\n        sanitize_error(1);', 'if (result == NULL) {\n        ;', "test_actual_sdk_key_derivation_failure_rich_diagnostics"),
    ("init-no-secret-local", 'account = os.environ.get("HEDERA_OPERATOR_ID")', 'secret = os.environ.get("HEDERA_OPERATOR_KEY")\n        account = os.environ.get("HEDERA_OPERATOR_ID")', "test_actual_sdk_backend_init_rich_diagnostics"),
    ("init-context-discard", 'failed = True\n        finally:\n            if failed and signer is not None:', 'failed = True\n            raise HederaError("Unsafe initialization context") from None\n        finally:\n            if failed and signer is not None:', "test_actual_sdk_backend_init_rich_diagnostics"),
    ("init-partial-signer-cleanup", 'if failed and signer is not None:\n                signer.__del__()', 'if failed and signer is not None:\n                pass', "test_actual_sdk_backend_init_rich_diagnostics"),
    ("control-code-redaction", 'code = error.code if type(error.code) is int or error.code is None else None', 'code = error.code', "test_actual_sdk_backend_init_rich_diagnostics"),
    ("admin-readback", '(state.get("admin_key") or {}).get("key") != self.backend.public_key', 'False', "test_topic_mismatch"),
    ("redaction", 'HederaError("Hedera submission unconfirmed; reconcile before retrying")', 'HederaError(str(__import__("sys").exception()))', "test_sdk_error_redaction"),
]


def main():
    try:
        import resource
    except ImportError:
        pass
    else:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    for label, before, after, test in MUTATIONS:
        native = label in {"native-automatic-owner", "native-error-redaction", "native-public-key-handoff",
                           "native-initializer-rollback", "native-initializer-error-redaction"}
        native = native or label == "native-initializer-operation-release"
        module = "hedera.py" if label == "environment-only" else "_hedera_signer_native.c" if native else "hedera_safe.py"
        source = (ROOT / "rpp/adapters" / module).read_text()
        assert source.count(before) == 1, label
        mutated = source.replace(before, after)
        if not module.endswith(".c"):
            compile(mutated, module, "exec")
        with tempfile.TemporaryDirectory(prefix="hedera-python-mutation-") as scratch:
            target = Path(scratch)
            shutil.copytree(ROOT / "rpp", target / "rpp", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy(ROOT / "tests/test_hedera_safe.py", target / "test_hedera_safe.py")
            shutil.copy(ROOT / "tests/test_hedera_sdk_security.py", target / "test_hedera_sdk_security.py")
            shutil.copy(ROOT / "tests/hedera_initializer_sigint_probe.py", target / "hedera_initializer_sigint_probe.py")
            (target / "rpp/adapters" / module).write_text(mutated)
            if module.endswith(".c"):
                subprocess.run([sys.executable, str(ROOT / "scripts/build_hedera_native.py"),
                                "--source", str(target / "rpp/adapters" / module),
                                "--output-dir", str(target / "rpp/adapters")],
                               check=True, capture_output=True, text=True, timeout=30)
            test_file = "test_hedera_sdk_security.py" if test.startswith("test_actual_") else "test_hedera_safe.py"
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", f"{test_file}::{test}"],
                                    cwd=target, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                    capture_output=True, text=True, timeout=90, check=False)
            assertion = "AssertionError" in result.stdout or "DID NOT RAISE" in result.stdout
            expected = {
                "native-initializer-boundary": "Escaped product traceback locals exposed a signing key",
                "native-initializer-rollback": "Failed initialization left an escaped signing handle open",
                "native-public-key-handoff": "Native initializer handed private signing state to Python",
            }.get(label)
            if result.returncode != 1 or "FAILED " + test_file + "::" + test not in result.stdout or not assertion:
                raise RuntimeError(f"Mutation {label} survived or did not fail its named assertion")
            if expected is not None and expected not in result.stdout:
                raise RuntimeError(f"Mutation {label} failed for an unrelated reason")
            print(f"KILLED {label}: {test}")


if __name__ == "__main__":
    main()
