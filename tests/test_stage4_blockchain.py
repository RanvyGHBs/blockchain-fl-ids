"""
Unit tests for Stage 4: Blockchain & Cryptographic Audit Ledger.
"""

import unittest
from src.blockchain.crypto import CryptoManager
from src.blockchain.block import Transaction, Block
from src.blockchain.chain import Blockchain


class TestBlockchain(unittest.TestCase):

    def test_01_ecdsa_signatures(self):
        priv_key, pub_key = CryptoManager.generate_keypair()
        message = "model_hash_98a72b0cf"
        signature = CryptoManager.sign_message(priv_key, message)

        # Valid verification
        self.assertTrue(CryptoManager.verify_signature(pub_key, message, signature))

        # Tampered message
        tampered_message = "model_hash_tampered_000"
        self.assertFalse(CryptoManager.verify_signature(pub_key, tampered_message, signature))

    def test_02_blockchain_flow(self):
        chain = Blockchain(committee_size=2)
        self.assertEqual(len(chain.chain), 1)  # Genesis block
        self.assertTrue(chain.is_chain_valid())

        # Create transactions
        tx1 = Transaction(
            client_id=0, round_num=1, weights_hash="hash_c0",
            signature="sig0", validation_metrics={"l2_norm": 2.1},
            status="ACCEPTED", reputation_before=1.0, reputation_after=1.05
        )
        tx2 = Transaction(
            client_id=1, round_num=1, weights_hash="hash_c1_poison",
            signature="sig1", validation_metrics={"l2_norm": 50.4},
            status="REJECTED", reputation_before=1.0, reputation_after=0.65
        )

        chain.add_transaction(tx1)
        chain.add_transaction(tx2)
        self.assertEqual(len(chain.mempool), 2)

        # Forge block
        validator = chain.select_validator({0: 1.05, 1: 0.65})
        new_block = chain.forge_block(global_model_hash="global_round_1_hash", validator_id=validator)

        self.assertEqual(len(chain.chain), 2)
        self.assertEqual(len(chain.mempool), 0)
        self.assertEqual(new_block.index, 1)
        self.assertEqual(len(new_block.transactions), 2)
        self.assertTrue(chain.is_chain_valid())

        # Test tampering detection
        chain.chain[1].previous_hash = "tampered_fake_hash"
        self.assertFalse(chain.is_chain_valid())


if __name__ == "__main__":
    unittest.main()
