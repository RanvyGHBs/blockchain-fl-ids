"""
Abstract Base Class for Network Intrusion Detection Datasets.
Ensures standardized loading, preprocessing, and interface consistency.
"""

from abc import ABC, abstractmethod
from typing import Dict, Tuple, Any, Optional
import numpy as np
import pandas as pd


class BaseDatasetLoader(ABC):
    """
    Abstract interface for cybersecurity dataset loaders.
    Any dataset (NSL-KDD, CIC-IDS2017, UNSW-NB15) must implement this interface.
    """

    def __init__(self, raw_dir: str, processed_dir: str, binary: bool = True, seed: int = 42):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.binary = binary
        self.seed = seed
        self.feature_names = []
        self.num_features = 0
        self.num_classes = 2 if binary else 5
        self.scaler = None
        self.label_encoder = None

    @abstractmethod
    def download_or_verify(self) -> bool:
        """Download dataset if absent, or generate/verify raw files."""
        pass

    @abstractmethod
    def load_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load train and test raw DataFrames."""
        pass

    @abstractmethod
    def preprocess(self, force: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Preprocess the raw data.
        Returns:
            X_train, y_train, X_test, y_test (as normalized numpy arrays)
        """
        pass

    @abstractmethod
    def get_feature_dimension(self) -> int:
        """Return the number of input features after one-hot encoding/scaling."""
        pass

    @abstractmethod
    def get_class_names(self) -> list:
        """Return human-readable class names."""
        pass
