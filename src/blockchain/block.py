"""
Block and Transaction Data Structures for Federated Audit Ledger.
Implements immutable transaction records, Merkle root calculation,
and cryptographic block chaining.
"""

import time
import json
import hashlib
from typing import List, Dict, Any, Optional


class Transaction:
    """
    Represents an auditable model update submission from a federated participant.
    """

    def __init__(self, client_id: int, round_num: int, weights_hash: str,
                 signature: str, validation_metrics: Dict[str, Any],
                 status: str, reputation_before: float, reputation_after: float,
                 timestamp: Optional[float] = None):
        self.client_id = client_id
        self.round_num = round_num
        self.weights_hash = weights_hash
        self.signature = signature
        self.validation_metrics = validation_metrics
        self.status = status.upper()  # "ACCEPTED" or "REJECTED"
        self.reputation_before = float(reputation_before)
        self.reputation_after = float(reputation_after)
        self.timestamp = timestamp or time.time()
        self.tx_id = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Computes unique SHA-256 transaction identifier."""
        tx_data = {
            "client_id": self.client_id,
            "round_num": self.round_num,
            "weights_hash": self.weights_hash,
            "signature": self.signature,
            "status": self.status,
            "timestamp": self.timestamp
        }
        encoded = json.dumps(tx_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "client_id": self.client_id,
            "round_num": self.round_num,
            "weights_hash": self.weights_hash,
            "signature": self.signature,
            "validation_metrics": self.validation_metrics,
            "status": self.status,
            "reputation_before": self.reputation_before,
            "reputation_after": self.reputation_after,
            "timestamp": self.timestamp
        }


class Block:
    """
    A single block in the trust audit blockchain.
    """

    def __init__(self, index: int, previous_hash: str, transactions: List[Transaction],
                 global_model_hash: str, validator_id: int = 0, timestamp: Optional[float] = None):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.global_model_hash = global_model_hash
        self.validator_id = validator_id
        self.merkle_root = self.calculate_merkle_root()
        self.hash = self.calculate_hash()

    def calculate_merkle_root(self) -> str:
        """Computes Merkle root of all transactions in this block."""
        if not self.transactions:
            return hashlib.sha256(b"empty_block").hexdigest()

        hashes = [tx.tx_id for tx in self.transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])  # Duplicate last hash if odd length
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = (hashes[i] + hashes[i + 1]).encode("utf-8")
                next_level.append(hashlib.sha256(combined).hexdigest())
            hashes = next_level

        return hashes[0]

    def calculate_hash(self) -> str:
        """Computes block SHA-256 checksum."""
        block_header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "global_model_hash": self.global_model_hash,
            "validator_id": self.validator_id
        }
        encoded = json.dumps(block_header, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "hash": self.hash,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "global_model_hash": self.global_model_hash,
            "validator_id": self.validator_id,
            "num_transactions": len(self.transactions),
            "transactions": [tx.to_dict() for tx in self.transactions]
        }
