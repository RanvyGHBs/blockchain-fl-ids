"""
Explainable AI (XAI) Attribution Engine.
Uses gradient-based input sensitivity (Input * Gradient) to explain why a particular
network-flow packet was classified as Normal or an Intrusion.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn


class FastFeatureExplainer:
    """
    Computes rapid, mathematically exact feature attributions for deep learning models.
    Supports both binary cybersecurity models and arbitrary multi-class classification models.
    """

    def __init__(self, model: nn.Module, feature_names: List[str], device: str = "cpu",
                 class_names: Optional[List[str]] = None):
        self.model = model
        self.feature_names = feature_names
        self.device = device
        self.class_names = class_names

    def explain_flow(self, flow_vector: np.ndarray, top_k: int = 5) -> Dict[str, Any]:
        """
        Explains prediction for a single normalized network flow or tabular feature vector.
        Returns:
            predicted_class, confidence, and top_k influential features with attribution scores.
        """
        self.model.eval()
        x_tensor = torch.from_numpy(flow_vector.reshape(1, -1)).float().to(self.device)
        x_tensor.requires_grad = True

        outputs = self.model(x_tensor)
        probs = torch.softmax(outputs, dim=1).detach().cpu().numpy()[0]
        pred_class = int(np.argmax(probs))
        confidence = float(probs[pred_class])

        # Compute gradient of target class score with respect to input features
        target_score = outputs[0, pred_class]
        target_score.backward()

        grads = x_tensor.grad.detach().cpu().numpy()[0]
        # Input * Gradient attribution
        attributions = np.abs(flow_vector * grads)

        # Rank features by absolute attribution importance
        top_indices = np.argsort(attributions)[::-1][:top_k]

        explanation_features = []
        for idx in top_indices:
            feat_name = self.feature_names[idx] if idx < len(self.feature_names) else f"feature_{idx}"
            explanation_features.append({
                "feature": feat_name,
                "value": float(flow_vector[idx]),
                "attribution_score": float(attributions[idx]),
                "relative_importance": float(attributions[idx] / (np.sum(attributions) + 1e-9))
            })

        # Dynamically determine human-readable class label
        if self.class_names and pred_class < len(self.class_names):
            class_label = self.class_names[pred_class]
        elif getattr(self.model, "num_classes", None) == 2 or (hasattr(self.model, "classifier") and self.model.classifier.out_features == 2):
            class_label = "Attack" if pred_class == 1 else "Normal"
        else:
            class_label = f"Class {pred_class}"

        return {
            "predicted_class": pred_class,
            "class_label": class_label,
            "confidence": confidence,
            "top_features": explanation_features
        }
