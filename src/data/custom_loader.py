"""
Custom Dataset Ingestion Engine (Track B: General-Purpose Federated Classification).
Enables importing user-supplied tabular datasets (CSV, DataFrames, in-memory buffers)
and built-in benchmark presets (Breast Cancer, Iris, Wine) with strict 3-way isolation.

Strict Isolation Principles:
1. Raw records are split into training and held-out test sets first.
2. Raw training records are split into client-training pool and validation benchmark.
3. Imputers, scalers, and encoders are fitted EXCLUSIVELY on client-training pool records.
4. Validation benchmark and held-out test sets are transformed using fitted objects.
5. Zero validation or test samples enter parameter fitting, local training, or model selection.
"""

import os
import io
import json
import pickle
from typing import Tuple, List, Dict, Any, Optional, Union
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, StandardScaler, OneHotEncoder, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.datasets import load_breast_cancer, load_iris, load_wine

from src.data.base_loader import BaseDatasetLoader


class CustomDatasetLoader(BaseDatasetLoader):
    """
    Ingestion engine for general-purpose tabular datasets in Federated Learning (Track B).
    Supports built-in presets ('breast_cancer', 'iris', 'wine'), CSV filepaths,
    DataFrames, and in-memory file buffers (e.g., Streamlit file uploader).
    """

    PRESETS = {
        "breast_cancer": "Breast Cancer Wisconsin (Diagnostic) — 30 features, binary",
        "iris": "Iris Flower Classification — 4 features, 3 classes",
        "wine": "Wine Recognition Dataset — 13 features, 3 classes"
    }

    def __init__(
        self,
        source: Union[str, pd.DataFrame, io.BytesIO, io.StringIO] = "breast_cancer",
        target_column: Optional[str] = None,
        dataset_name: Optional[str] = None,
        raw_dir: str = "data/raw/custom",
        processed_dir: str = "data/processed/custom",
        test_size: float = 0.2,
        val_size: Union[int, float] = 0.15,
        scaler_type: str = "minmax",
        seed: int = 42
    ):
        super().__init__(raw_dir=raw_dir, processed_dir=processed_dir, binary=True, seed=seed)
        self.source = source
        self.target_column = target_column
        self.dataset_name = dataset_name or self._infer_dataset_name(source)
        self.test_size = test_size
        self.val_size = val_size
        self.scaler_type = scaler_type.lower()
        
        # State populated upon loading/preprocessing
        self.raw_df: Optional[pd.DataFrame] = None
        self.feature_columns: List[str] = []
        self.numeric_columns: List[str] = []
        self.categorical_columns: List[str] = []
        self.class_names: List[str] = []
        self.num_classes: int = 2
        self.num_features: int = 0
        
        # Preprocessing artifacts fitted strictly on client-training pool
        self.num_imputer: Optional[SimpleImputer] = None
        self.cat_imputer: Optional[SimpleImputer] = None
        self.encoder: Optional[OneHotEncoder] = None
        self.label_encoder: Optional[LabelEncoder] = None

    def _infer_dataset_name(self, source: Any) -> str:
        if isinstance(source, str):
            if source in self.PRESETS:
                return source
            return os.path.splitext(os.path.basename(source))[0]
        if isinstance(source, pd.DataFrame):
            return "Custom_DataFrame"
        return "Uploaded_Dataset"

    def download_or_verify(self) -> bool:
        """Verifies directory structures exist."""
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        return True

    def load_raw_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads raw data from preset, filepath, DataFrame, or uploaded buffer.
        Returns:
            df_train_raw, df_test_raw (split strictly before any preprocessing)
        """
        self.download_or_verify()

        if isinstance(self.source, str) and self.source in self.PRESETS:
            df = self._load_preset(self.source)
        elif isinstance(self.source, str) and os.path.isfile(self.source):
            df = pd.read_csv(self.source)
        elif isinstance(self.source, pd.DataFrame):
            df = self.source.copy()
        elif hasattr(self.source, "read"):
            # Streamlit UploadedFile or BytesIO / StringIO
            if hasattr(self.source, "seek"):
                self.source.seek(0)
            df = pd.read_csv(self.source)
        else:
            raise ValueError(f"Unsupported data source: {type(self.source)}. Expected preset, filepath, or DataFrame.")

        if len(df) < 20:
            raise ValueError(f"Dataset too small ({len(df)} rows). Minimum required is 20 rows.")

        # Determine target column
        if self.target_column is None:
            self.target_column = self._auto_detect_target_column(df)
        elif self.target_column not in df.columns:
            raise ValueError(f"Specified target column '{self.target_column}' not found in dataset columns: {list(df.columns)}")

        self.raw_df = df

        # Ensure target column has at least 2 distinct classes
        unique_targets = df[self.target_column].dropna().unique()
        if len(unique_targets) < 2:
            raise ValueError(f"Target column '{self.target_column}' must have at least 2 classes. Found: {unique_targets}")

        y_raw = df[self.target_column].values

        # Step 1: Split into raw development/training and independent held-out test set
        df_train_raw, df_test_raw = train_test_split(
            df,
            test_size=self.test_size,
            random_state=self.seed,
            stratify=y_raw
        )

        return df_train_raw, df_test_raw

    def _auto_detect_target_column(self, df: pd.DataFrame) -> str:
        """Infers the target column from standard naming or defaults to the last column."""
        candidates = ["target", "label", "class", "diagnosis", "attack", "outcome", "y"]
        for c in candidates:
            for col in df.columns:
                if col.lower() == c:
                    return col
        return df.columns[-1]

    def _load_preset(self, preset_name: str) -> pd.DataFrame:
        """Loads a built-in standard scikit-learn dataset formatted as a DataFrame."""
        if preset_name == "breast_cancer":
            data = load_breast_cancer(as_frame=True)
            df = data.frame.copy()
            self.target_column = "target"
        elif preset_name == "iris":
            data = load_iris(as_frame=True)
            df = data.frame.copy()
            self.target_column = "target"
        elif preset_name == "wine":
            data = load_wine(as_frame=True)
            df = data.frame.copy()
            self.target_column = "target"
        else:
            raise ValueError(f"Unknown preset: {preset_name}")
        return df

    def preprocess(self, force: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Standard 2-way preprocessing for backwards compatibility with BaseDatasetLoader.
        Returns:
            X_train, y_train, X_test, y_test
        """
        X_train_pool, y_train_pool, _, _, X_test, y_test = self.preprocess_isolated(force=force)
        return X_train_pool, y_train_pool, X_test, y_test

    def preprocess_isolated(
        self,
        force: bool = False,
        val_size: Optional[Union[int, float]] = None,
        test_size: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Executes strict 3-way research-grade dataset isolation:
        1. Split raw data into dev/train and held-out test sets.
        2. Split dev/train data into client-training pool and validation benchmark.
        3. Fit imputers, encoders, and scalers EXCLUSIVELY on client-training pool.
        4. Transform validation benchmark and test set using fitted objects.
        5. Never use validation or test records for parameter fitting.

        Returns:
            X_train_pool, y_train_pool, X_val, y_val, X_test, y_test
        """
        if val_size is not None:
            self.val_size = val_size
        if test_size is not None:
            self.test_size = test_size

        df_train_raw, df_test_raw = self.load_raw_data()

        y_train_raw = df_train_raw[self.target_column].values

        # Determine validation split sample count
        if isinstance(self.val_size, float):
            val_samples = max(2, int(len(df_train_raw) * self.val_size))
        else:
            val_samples = min(self.val_size, max(2, int(len(df_train_raw) * 0.3)))

        # Step 2: Split dev/train into client-training pool and trust-validation benchmark
        df_pool_raw, df_val_raw = train_test_split(
            df_train_raw,
            test_size=val_samples,
            random_state=self.seed,
            stratify=y_train_raw
        )

        # Separate feature columns from target
        feature_cols = [c for c in df_pool_raw.columns if c != self.target_column]
        self.numeric_columns = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df_pool_raw[c])]
        self.categorical_columns = [c for c in feature_cols if c not in self.numeric_columns]

        df_pool_feat = df_pool_raw[feature_cols].copy()
        df_val_feat = df_val_raw[feature_cols].copy()
        df_test_feat = df_test_raw[feature_cols].copy()

        y_pool_raw = df_pool_raw[self.target_column].values
        y_val_raw = df_val_raw[self.target_column].values
        y_test_raw = df_test_raw[self.target_column].values

        # Step 3: Imputation (fitted strictly on pool)
        if self.numeric_columns:
            self.num_imputer = SimpleImputer(strategy="median")
            num_pool = self.num_imputer.fit_transform(df_pool_feat[self.numeric_columns])
            num_val = self.num_imputer.transform(df_val_feat[self.numeric_columns])
            num_test = self.num_imputer.transform(df_test_feat[self.numeric_columns])
        else:
            num_pool = np.empty((len(df_pool_feat), 0))
            num_val = np.empty((len(df_val_feat), 0))
            num_test = np.empty((len(df_test_feat), 0))

        if self.categorical_columns:
            self.cat_imputer = SimpleImputer(strategy="most_frequent")
            cat_pool = self.cat_imputer.fit_transform(df_pool_feat[self.categorical_columns])
            cat_val = self.cat_imputer.transform(df_val_feat[self.categorical_columns])
            cat_test = self.cat_imputer.transform(df_test_feat[self.categorical_columns])

            # Step 4: Categorical One-Hot Encoding (fitted strictly on pool)
            self.encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
            cat_pool_enc = self.encoder.fit_transform(cat_pool)
            cat_val_enc = self.encoder.transform(cat_val)
            cat_test_enc = self.encoder.transform(cat_test)
            cat_feature_names = list(self.encoder.get_feature_names_out(self.categorical_columns))
        else:
            cat_pool_enc = np.empty((len(df_pool_feat), 0))
            cat_val_enc = np.empty((len(df_val_feat), 0))
            cat_test_enc = np.empty((len(df_test_feat), 0))
            cat_feature_names = []

        # Step 5: Numeric Feature Scaling (fitted strictly on pool)
        if self.numeric_columns:
            if self.scaler_type == "standard":
                self.scaler = StandardScaler()
            else:
                self.scaler = MinMaxScaler()
            
            num_pool_scaled = self.scaler.fit_transform(num_pool).astype(np.float32)
            num_val_scaled = self.scaler.transform(num_val).astype(np.float32)
            num_test_scaled = self.scaler.transform(num_test).astype(np.float32)
        else:
            num_pool_scaled = np.empty((len(df_pool_feat), 0), dtype=np.float32)
            num_val_scaled = np.empty((len(df_val_feat), 0), dtype=np.float32)
            num_test_scaled = np.empty((len(df_test_feat), 0), dtype=np.float32)

        # Assemble final feature matrices
        X_train_pool = np.hstack([num_pool_scaled, cat_pool_enc]).astype(np.float32)
        X_val = np.hstack([num_val_scaled, cat_val_enc]).astype(np.float32)
        X_test = np.hstack([num_test_scaled, cat_test_enc]).astype(np.float32)

        self.feature_columns = list(self.numeric_columns) + cat_feature_names
        self.num_features = X_train_pool.shape[1]

        # Step 6: Target Label Encoding (fitted strictly on pool)
        self.label_encoder = LabelEncoder()
        y_train_pool = self.label_encoder.fit_transform(y_pool_raw).astype(np.int64)
        
        # Safe transform for validation and test with fallback for unobserved labels
        def safe_transform_labels(le: LabelEncoder, targets: np.ndarray) -> np.ndarray:
            known_classes = set(le.classes_)
            transformed = []
            default_label = 0
            for t in targets:
                if t in known_classes:
                    transformed.append(le.transform([t])[0])
                else:
                    transformed.append(default_label)
            return np.array(transformed, dtype=np.int64)

        y_val = safe_transform_labels(self.label_encoder, y_val_raw)
        y_test = safe_transform_labels(self.label_encoder, y_test_raw)

        self.class_names = [str(c) for c in self.label_encoder.classes_]
        self.num_classes = len(self.class_names)
        self.binary = (self.num_classes == 2)

        return X_train_pool, y_train_pool, X_val, y_val, X_test, y_test

    def get_feature_dimension(self) -> int:
        return self.num_features

    def get_num_classes(self) -> int:
        return self.num_classes

    def get_class_names(self) -> List[str]:
        return self.class_names

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured metadata summary for UI inspection and verification."""
        if self.raw_df is None:
            self.load_raw_data()
        
        counts = pd.Series(self.raw_df[self.target_column]).value_counts().to_dict()
        class_dist = {str(k): int(v) for k, v in counts.items()}

        return {
            "dataset_name": self.dataset_name,
            "total_samples": len(self.raw_df),
            "target_column": self.target_column,
            "num_features": self.num_features or len(self.raw_df.columns) - 1,
            "numeric_columns_count": len(self.numeric_columns),
            "categorical_columns_count": len(self.categorical_columns),
            "num_classes": self.num_classes,
            "class_names": self.class_names or [str(k) for k in class_dist.keys()],
            "class_distribution": class_dist,
            "is_binary": len(class_dist) == 2,
            "test_split_ratio": self.test_size,
            "val_split_ratio": self.val_size
        }
