"""Experimental testnet smoke; never grants mainnet access or loads key files."""
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rpp.adapters.hedera_safe import HederaError, Session


def main():
    if os.environ.get("HEDERA_NETWORK", "testnet") != "testnet":
        print("BLOCKED: this smoke only permits testnet")
        return 2
    if os.environ.get("HEDERA_TESTNET_THROWAWAY") != "true":
        print("BLOCKED: HEDERA_TESTNET_THROWAWAY=true runtime attestation required")
        return 2
    if not all(os.environ.get(name) for name in ("HEDERA_OPERATOR_ID", "HEDERA_OPERATOR_KEY")):
        print("BLOCKED: no runtime throwaway testnet account; no write attempted")
        return 2
    session = None
    try:
        session = Session.from_env()
        topic = session.create_topic("hedera-day1-python-smoke")["topic_id"]
        payload = json.dumps({"product": "rpp-reference", "nonce": uuid.uuid4().hex}).encode()
        signed = session.signed_record(payload)
        receipt = session.submit(topic, signed)
        assert receipt["data"] == signed
        print(json.dumps({"network": "testnet", "topic_id": topic, "sequence": receipt["sequence"],
                          "transaction_id": receipt["transaction_id"], "verified_bytes": len(signed),
                          "sdk_support": "community-pre-alpha-experimental"}))
        return 0
    except HederaError as error:
        print(f"BLOCKED: {error}")
        return 2
    except Exception:  # noqa: BLE001 - SDK errors may contain secrets; sanitize boundary
        print("FAILED: smoke unconfirmed; inspect receipts before retrying")
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
