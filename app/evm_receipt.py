"""One bounded Base transaction-receipt product unit.

The unit makes exactly two read-only JSON-RPC calls: receipt plus observed head.
It never sends, signs, simulates, or modifies a transaction.
"""
from __future__ import annotations

import json
import os
import re
from urllib.request import Request, urlopen


DEFAULT_BASE_RPC_URL = "https://mainnet.base.org"
TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


class RpcError(RuntimeError):
    """The upstream RPC did not return a usable JSON-RPC result."""


def _rpc_call(method: str, params: list, rpc_url: str, timeout_seconds: float) -> object:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = Request(
        rpc_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PinkHive-EVM-Receipt/1.0 (+https://github.com/1355-XCZ-O/pinkhive-website-prep-x402)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RpcError(f"Base RPC request failed for {method}") from exc
    if not isinstance(payload, dict) or payload.get("error") is not None or "result" not in payload:
        raise RpcError(f"Base RPC returned an invalid result for {method}")
    return payload["result"]


def _hex_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.startswith("0x"):
        raise RpcError("Base RPC returned a malformed hexadecimal quantity")
    return int(value, 16)


def query_base_receipt(payload: dict, rpc_url: str | None = None, timeout_seconds: float = 5.0) -> dict:
    """Return a normalized receipt at one observed Base-mainnet head."""
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    tx_hash = payload.get("tx_hash")
    if not isinstance(tx_hash, str) or not TX_HASH.fullmatch(tx_hash):
        raise ValueError("tx_hash must be a 0x-prefixed 32-byte hexadecimal transaction hash")

    endpoint = rpc_url or os.environ.get("BASE_RPC_URL", DEFAULT_BASE_RPC_URL)
    receipt = _rpc_call("eth_getTransactionReceipt", [tx_hash], endpoint, timeout_seconds)
    observed_head = _hex_int(_rpc_call("eth_blockNumber", [], endpoint, timeout_seconds))
    canonical_hash = tx_hash.lower()

    if receipt is None:
        return {
            "chain_id": 8453,
            "network": "base-mainnet",
            "tx_hash": canonical_hash,
            "state": "not_found_or_pending",
            "observed_head": observed_head,
            "block_number": None,
            "confirmations": 0,
            "success": None,
            "from": None,
            "to": None,
            "contract_address": None,
            "gas_used": None,
            "effective_gas_price_wei": None,
            "log_count": 0,
            "rpc_calls": 2,
        }

    if not isinstance(receipt, dict):
        raise RpcError("Base RPC returned a malformed transaction receipt")
    block_number = _hex_int(receipt.get("blockNumber"))
    status = _hex_int(receipt.get("status"))
    if block_number is None or status not in (0, 1):
        raise RpcError("Base RPC receipt is missing blockNumber or status")
    return {
        "chain_id": 8453,
        "network": "base-mainnet",
        "tx_hash": canonical_hash,
        "state": "confirmed",
        "observed_head": observed_head,
        "block_number": block_number,
        "confirmations": max(0, observed_head - block_number + 1),
        "success": status == 1,
        "from": receipt.get("from"),
        "to": receipt.get("to"),
        "contract_address": receipt.get("contractAddress"),
        "gas_used": _hex_int(receipt.get("gasUsed")),
        "effective_gas_price_wei": _hex_int(receipt.get("effectiveGasPrice")),
        "log_count": len(receipt.get("logs", [])) if isinstance(receipt.get("logs", []), list) else 0,
        "rpc_calls": 2,
    }
