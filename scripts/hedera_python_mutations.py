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
    ("opaque-signer-repr", 'return "<HederaSigner redacted>"', 'return repr(self.__operation)', "test_actual_sdk_signer_inspection_is_redacted"),
    ("admin-readback", '(state.get("admin_key") or {}).get("key") != self.backend.public_key', 'False', "test_topic_mismatch"),
    ("redaction", 'HederaError("Hedera submission unconfirmed; reconcile before retrying")', 'HederaError(str(__import__("sys").exception()))', "test_sdk_error_redaction"),
]


def main():
    for label, before, after, test in MUTATIONS:
        module = "hedera.py" if label == "environment-only" else "hedera_safe.py"
        source = (ROOT / "rpp/adapters" / module).read_text()
        assert source.count(before) == 1, label
        mutated = source.replace(before, after)
        compile(mutated, "hedera_safe.py", "exec")
        with tempfile.TemporaryDirectory(prefix="hedera-python-mutation-") as scratch:
            target = Path(scratch)
            shutil.copytree(ROOT / "rpp", target / "rpp", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copy(ROOT / "tests/test_hedera_safe.py", target / "test_hedera_safe.py")
            shutil.copy(ROOT / "tests/test_hedera_sdk_security.py", target / "test_hedera_sdk_security.py")
            (target / "rpp/adapters" / module).write_text(mutated)
            test_file = "test_hedera_sdk_security.py" if test.startswith("test_actual_") else "test_hedera_safe.py"
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", f"{test_file}::{test}"],
                                    cwd=target, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                    capture_output=True, text=True, timeout=30, check=False)
            if result.returncode != 1 or "FAILED " + test_file + "::" + test not in result.stdout:
                raise RuntimeError(f"Mutation {label} survived or did not fail its named assertion")
            print(f"KILLED {label}: {test}")


if __name__ == "__main__":
    main()
