"""
PyTorch Deep Neural Network for Network Intrusion Detection.
Provides parameter serialization, 1D vector conversion, and SHA-256 weight hashing
for federated aggregation and blockchain verification.
"""

import hashlib
from typing import Dict, Any, Tuple
import numpy as np
import torch
import torch.nn as nn


class IDSNet(nn.Module):
    """
    Multi-Layer Perceptron (MLP) for Network Intrusion Detection.
    Optimized for tabular flow features with Batch Normalization and Dropout regularization.
    """

    def __init__(self, input_dim: int = 122, num_classes: int = 2, hidden_dims: Tuple[int, ...] = (128, 64, 32),
                 dropout_rate: float = 0.2):
        super(IDSNet, self).__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        layers = []
        prev_dim = input_dim
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(nn.BatchNorm1d(h_dim))
            layers.append(nn.ReLU())
            if dropout_rate > 0.0:
                layers.append(nn.Dropout(dropout_rate))
            prev_dim = h_dim

        self.feature_extractor = nn.Sequential(*layers)
        self.classifier = nn.Linear(prev_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature_extractor(x)
        logits = self.classifier(features)
        return logits

    def get_weights_vector(self) -> np.ndarray:
        """
        Flattens all trainable parameters into a single 1D float32 numpy array.
        Essential for vector math (cosine similarity, Euclidean distance, FoolsGold).
        """
        weights = []
        for param in self.parameters():
            weights.append(param.detach().cpu().numpy().flatten())
        return np.concatenate(weights).astype(np.float32)

    def set_weights_vector(self, flat_weights: np.ndarray):
        """
        Restores model parameters from a flattened 1D float32 numpy array.
        """
        offset = 0
        state_dict = self.state_dict()
        for name, param in self.named_parameters():
            param_shape = param.shape
            param_size = param.numel()
            param_data = flat_weights[offset: offset + param_size].reshape(param_shape)
            state_dict[name].copy_(torch.from_numpy(param_data))
            offset += param_size

    def get_weights_hash(self) -> str:
        """
        Computes the SHA-256 cryptographic checksum of current model parameters.
        Used by the blockchain layer for immutable record-keeping.
        """
        flat_weights = self.get_weights_vector()
        return hashlib.sha256(flat_weights.tobytes()).hexdigest()

    def get_parameter_count(self) -> int:
        """Returns total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
