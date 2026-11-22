"""
Blockchain Ledger and Proof-of-Trust Consensus.
Coordinates transaction mempools, validator selection, block minting,
and immutable chain verification.
"""

from typing import List, Dict, Any, Optional
from src.blockchain.block import Block, Transaction


class Blockchain:
    """
    Decentralized Trust Ledger for Federated Learning.
    Maintains an immutable, cryptographically verifiable record of all training rounds,
    model checksums, accepted contributions, and slashed adversarial attacks.
    """

    def __init__(self, committee_size: int = 3):
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []
        self.committee_size = committee_size
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Mints the initial Genesis Block (Height 0)."""
        genesis_block = Block(
            index=0,
            previous_hash="0" * 64,
            transactions=[],
            global_model_hash="genesis_initial_model_hash",
            validator_id=-1,
            timestamp=0.0
        )
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction):
        """Adds an auditable model update transaction to the mempool."""
        self.mempool.append(transaction)

    def select_validator(self, client_reputations: Dict[int, float]) -> int:
        """
        Proof-of-Trust (PoT) Consensus:
        Selects the block proposer from the top-reputation honest participants.
        """
        if not client_reputations:
            return 0
        sorted_clients = sorted(client_reputations.items(), key=lambda x: x[1], reverse=True)
        top_candidates = [cid for cid, score in sorted_clients[:self.committee_size]]
        # Deterministic rotation based on current block height
        selected_validator = top_candidates[len(self.chain) % len(top_candidates)]
        return selected_validator

    def forge_block(self, global_model_hash: str, validator_id: int) -> Block:
        """
        Mints a new block containing all mempool transactions,
        links it cryptographically to the parent block, and empties the mempool.
        """
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            previous_hash=latest_block.hash,
            transactions=list(self.mempool),
            global_model_hash=global_model_hash,
            validator_id=validator_id
        )

        self.chain.append(new_block)
        self.mempool.clear()
        return new_block

    def is_chain_valid(self) -> bool:
        """
        Cryptographically verifies the entire blockchain:
        1. Current block hash matches its calculated SHA-256 header.
        2. Previous hash matches parent block hash.
        3. Merkle root of transactions is valid.
        """
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]

            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr.calculate_hash():
                return False
            if curr.merkle_root != curr.calculate_merkle_root():
                return False

        return True

    def get_all_blocks_dict(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self.chain]

    def get_audit_summary(self) -> Dict[str, Any]:
        """Provides high-level audit metrics for the dashboard."""
        total_blocks = len(self.chain)
        all_txs = [tx for b in self.chain for tx in b.transactions]
        accepted_txs = [tx for tx in all_txs if tx.status == "ACCEPTED"]
        rejected_txs = [tx for tx in all_txs if tx.status == "REJECTED"]

        return {
            "total_blocks": total_blocks,
            "total_transactions": len(all_txs),
            "accepted_transactions": len(accepted_txs),
            "rejected_attacks": len(rejected_txs),
            "is_chain_valid": self.is_chain_valid()
        }
