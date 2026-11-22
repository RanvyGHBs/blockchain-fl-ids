"""
Federated Dataset Partitioner.
Partitions training data across K independent clients using either:
1. Non-IID Dirichlet distribution (Dir(alpha)).
2. IID uniform distribution.
Provides client statistics and class distribution matrices.
"""

from typing import Dict, List, Tuple, Any
import numpy as np


class FederatedPartitioner:
    """
    Partitions datasets across multiple independent federated clients.
    """

    def __init__(self, num_clients: int = 5, non_iid: bool = True, alpha: float = 0.5, seed: int = 42):
        self.num_clients = num_clients
        self.non_iid = non_iid
        self.alpha = alpha
        self.seed = seed

    def partition(self, X: np.ndarray, y: np.ndarray) -> Dict[int, Tuple[np.ndarray, np.ndarray]]:
        """
        Partitions X and y across clients.
        Returns:
            Dict mapping client_id -> (X_client, y_client)
        """
        np.random.seed(self.seed)
        num_samples = len(y)
        unique_classes = np.unique(y)
        num_classes = len(unique_classes)

        client_indices: Dict[int, List[int]] = {i: [] for i in range(self.num_clients)}

        if not self.non_iid:
            # IID: Uniform random shuffling and splitting
            indices = np.random.permutation(num_samples)
            splits = np.array_split(indices, self.num_clients)
            for cid in range(self.num_clients):
                client_indices[cid] = list(splits[cid])
        else:
            # Non-IID: Dirichlet distribution on class labels
            for c in unique_classes:
                c_indices = np.where(y == c)[0]
                np.random.shuffle(c_indices)
                num_c_samples = len(c_indices)

                # Sample Dirichlet distribution across K clients
                proportions = np.random.dirichlet(np.repeat(self.alpha, self.num_clients))
                proportions = proportions / proportions.sum()

                # Split class samples according to sampled proportions
                split_points = (np.cumsum(proportions)[:-1] * num_c_samples).astype(int)
                class_splits = np.split(c_indices, split_points)

                for cid in range(self.num_clients):
                    client_indices[cid].extend(class_splits[cid])

        # Construct final client datasets
        client_datasets: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
        for cid in range(self.num_clients):
            idx = np.array(client_indices[cid])
            if len(idx) == 0:
                # Edge case safeguard: ensure at least some samples
                idx = np.random.choice(num_samples, size=min(50, num_samples), replace=False)
            np.random.shuffle(idx)
            client_datasets[cid] = (X[idx], y[idx])

        return client_datasets

    def get_distribution_stats(self, client_datasets: Dict[int, Tuple[np.ndarray, np.ndarray]], 
                               class_names: List[str] = None) -> Dict[str, Any]:
        """
        Calculates distribution statistics across clients for visualization.
        """
        stats = {
            "num_clients": len(client_datasets),
            "client_sample_counts": {},
            "client_class_counts": {},
            "proportions": {}
        }

        all_classes = sorted(list(set(c for _, (_, y) in client_datasets.items() for c in np.unique(y))))

        for cid, (_, y) in client_datasets.items():
            stats["client_sample_counts"][cid] = len(y)
            counts = {int(c): int(np.sum(y == c)) for c in all_classes}
            stats["client_class_counts"][cid] = counts

        return stats
