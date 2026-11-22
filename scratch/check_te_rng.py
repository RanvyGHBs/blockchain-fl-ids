import sys
sys.path.insert(0, '.')
import torch
from src.trust.evaluator import MultiCriteriaTrustEngine

te = MultiCriteriaTrustEngine(10, 2)
w = te.validator_model.get_weights_vector()
val_data = (torch.randn(20, 10).numpy(), torch.randint(0, 2, (20,)).numpy())

rng_before = torch.get_rng_state()
te.evaluate_updates({0: w, 1: w}, w, val_data)
rng_after = torch.get_rng_state()

print("Does evaluate_updates change torch RNG state?", not torch.equal(rng_before, rng_after))
