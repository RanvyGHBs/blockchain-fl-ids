"""
Dynamic Reputation & Quarantine Management.
Implements asymmetric slashing, historical reputation decay,
quarantine thresholds, and shadow probation recovery.
"""

from typing import Dict, List, Any

from src.config import validate_reputation_params


class ReputationManager:
    """
    Manages client reputation scores, quarantine statuses, and rehabilitation.
    """

    def __init__(self, client_ids: List[int], initial_reputation: float = 1.0,
                 reward_delta: float = 0.05, slash_delta: float = 0.35,
                 quarantine_threshold: float = 0.40, probation_rounds: int = 3):
        validate_reputation_params(
            client_ids=client_ids,
            initial_reputation=initial_reputation,
            reward_delta=reward_delta,
            slash_delta=slash_delta,
            quarantine_threshold=quarantine_threshold,
            probation_rounds=probation_rounds,
        )
        self.reward_delta = reward_delta
        self.slash_delta = slash_delta
        self.quarantine_threshold = quarantine_threshold
        self.probation_rounds = probation_rounds

        self.reputations: Dict[int, float] = {cid: float(initial_reputation) for cid in client_ids}
        self.quarantine_status: Dict[int, bool] = {cid: False for cid in client_ids}
        self.probation_counters: Dict[int, int] = {cid: 0 for cid in client_ids}
        self.reputation_history: Dict[int, List[float]] = {cid: [float(initial_reputation)] for cid in client_ids}

    def update_reputation(self, validation_results: Dict[int, Dict[str, Any]]):
        """
        Updates reputation scores based on round validation results.
        Asymmetric scoring: Trust is slow to build and fast to lose.
        """
        for cid, result in validation_results.items():
            if cid not in self.reputations:
                self.reputations[cid] = 1.0
                self.quarantine_status[cid] = False
                self.probation_counters[cid] = 0
                self.reputation_history[cid] = [1.0]

            is_valid = result.get("is_valid", False)
            current_rep = self.reputations[cid]

            if is_valid:
                # Honest update: slow incremental reward
                new_rep = min(1.0, current_rep + self.reward_delta)
                if self.quarantine_status[cid]:
                    # In shadow probation
                    self.probation_counters[cid] += 1
                    if self.probation_counters[cid] >= self.probation_rounds:
                        # Rehabilitated! Readmit client to active pool
                        self.quarantine_status[cid] = False
                        self.probation_counters[cid] = 0
                        new_rep = 0.50  # Readmission baseline
                self.reputations[cid] = round(new_rep, 4)
            else:
                # Malicious update: severe asymmetric penalty
                new_rep = max(0.0, current_rep - self.slash_delta)
                self.reputations[cid] = round(new_rep, 4)
                self.probation_counters[cid] = 0  # Reset probation progress

                # Check quarantine threshold
                if self.reputations[cid] < self.quarantine_threshold:
                    self.quarantine_status[cid] = True

            self.reputation_history[cid].append(self.reputations[cid])

    def get_reputation(self, client_id: int) -> float:
        return self.reputations.get(client_id, 0.0)

    def is_quarantined(self, client_id: int) -> bool:
        return self.quarantine_status.get(client_id, False)

    def get_all_reputations(self) -> Dict[int, float]:
        return dict(self.reputations)

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "reputations": dict(self.reputations),
            "quarantined_clients": [cid for cid, q in self.quarantine_status.items() if q],
            "active_clients": [cid for cid, q in self.quarantine_status.items() if not q],
            "history": {cid: list(h) for cid, h in self.reputation_history.items()}
        }
