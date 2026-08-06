import unittest
from unittest.mock import patch

from app.evm_receipt import RpcError, query_base_receipt


HASH = "0x" + "ab" * 32


class EvmReceiptTests(unittest.TestCase):
    def test_rejects_non_hash_without_rpc(self):
        with patch("app.evm_receipt._rpc_call") as rpc:
            with self.assertRaisesRegex(ValueError, "32-byte"):
                query_base_receipt({"tx_hash": "0x123"})
            rpc.assert_not_called()

    @patch("app.evm_receipt._rpc_call")
    def test_normalizes_confirmed_receipt(self, rpc):
        rpc.side_effect = [{"blockNumber":"0x64","status":"0x1","from":"0xfrom","to":"0xto","contractAddress":None,"gasUsed":"0x5208","effectiveGasPrice":"0x3b9aca00","logs":[{},{}]}, "0x66"]
        result = query_base_receipt({"tx_hash": HASH}, rpc_url="https://rpc.invalid")
        self.assertEqual(result["state"], "confirmed")
        self.assertTrue(result["success"])
        self.assertEqual(result["block_number"], 100)
        self.assertEqual(result["confirmations"], 3)
        self.assertEqual(result["gas_used"], 21000)
        self.assertEqual(result["log_count"], 2)
        self.assertEqual(result["rpc_calls"], 2)
        self.assertEqual(rpc.call_count, 2)

    @patch("app.evm_receipt._rpc_call")
    def test_normalizes_pending_or_unknown(self, rpc):
        rpc.side_effect = [None, "0x66"]
        result = query_base_receipt({"tx_hash": HASH})
        self.assertEqual(result["state"], "not_found_or_pending")
        self.assertIsNone(result["success"])
        self.assertEqual(result["confirmations"], 0)

    @patch("app.evm_receipt._rpc_call")
    def test_rejects_malformed_receipt(self, rpc):
        rpc.side_effect = [{"blockNumber": "0x64"}, "0x66"]
        with self.assertRaises(RpcError):
            query_base_receipt({"tx_hash": HASH})


if __name__ == "__main__":
    unittest.main()
