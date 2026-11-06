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
    ("RADIX-gate", 'if self.network == "mainnet" and os.environ.get("RADIX_HEDERA_MAINNET_ENABLED") != "true":', 'if False:', "test_mainnet_guard"),
    ("environment-only", 'if operator_account is not None or operator_key is not None:', 'if False:', "test_experimental_gate_and_env_only"),
    ("experimental-gate", 'if os.environ.get("HEDERA_EXPERIMENTAL_PYTHON_ENABLED") != "true":', 'if False:', "test_experimental_gate_and_env_only"),
    ("fee-cap", 'transaction.transaction_fee = config.fee_tinybars', 'pass', "test_sdk_transaction_policy"),
    ("bounded-sdk-retry", 'transaction.set_max_attempts(config.attempts)', 'pass', "test_sdk_transaction_policy"),
    ("signed-transaction", '.sign_with_operator(self.client)', '', "test_sdk_transaction_policy"),
    ("receipt-success", 'if receipt.get("status") != 22:', 'if False:', "test_receipt_failure"),
    ("topic-readback", 'state.get("memo") != memo', 'False', "test_topic_mismatch"),
    ("create-tx-readback", 'if not any(t.get("transaction_id")', 'if False and not any(t.get("transaction_id")', "test_create_transaction_mismatch"),
    ("message-bytes", 'actual != payload', 'False', "test_message_mismatch"),
    ("message-topic", 'observed.get("topic_id") != topic', 'False', "test_message_mismatch"),
    ("message-payer", 'observed.get("payer_account_id") != self.backend.operator_id', 'False', "test_message_mismatch"),
    ("mirror-retry", 'range(self.config.mirror_attempts)', 'range(1)', "test_mirror_retry_bound"),
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
            (target / "rpp/adapters" / module).write_text(mutated)
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", f"test_hedera_safe.py::{test}"],
                                    cwd=target, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                                    capture_output=True, text=True, timeout=30, check=False)
            if result.returncode != 1 or "FAILED test_hedera_safe.py::" + test not in result.stdout:
                raise RuntimeError(f"Mutation {label} survived or did not fail its named assertion")
            print(f"KILLED {label}: {test}")


if __name__ == "__main__":
    main()
