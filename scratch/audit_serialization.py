import sys
import os
sys.path.insert(0, os.path.abspath("."))
import pickle
import pickletools
import numpy as np
import torch
from src.models.ids_net import IDSNet

model = IDSNet(input_dim=122, num_classes=2)
print("=== IDSNet PARAMETER & BUFFER AUDIT ===")

total_params = 0
for name, param in model.named_parameters():
    count = param.numel()
    total_params += count
    print(f"Param: {name:<35} | Shape: {str(list(param.shape)):<15} | Elements: {count:6d} | Dtype: {param.dtype} | Requires Grad: {param.requires_grad}")

print(f"\nTotal Trainable Parameters: {total_params}")

total_buffers = 0
for name, buf in model.named_buffers():
    count = buf.numel()
    total_buffers += count
    print(f"Buffer: {name:<35} | Shape: {str(list(buf.shape)):<15} | Elements: {count:6d} | Dtype: {buf.dtype}")

print(f"Total Non-trainable Buffers: {total_buffers}")

# Vector extracted by get_weights_vector()
weights_vec = model.get_weights_vector()
print(f"\nWeights Vector Shape: {weights_vec.shape}, Dtype: {weights_vec.dtype}, Length: {len(weights_vec)}")
raw_nbytes = weights_vec.nbytes
print(f"Raw ndarray bytes (len * 4): {raw_nbytes} bytes")

# Pickle serialization
pickled = pickle.dumps(weights_vec)
pickle_len = len(pickled)
diff = pickle_len - raw_nbytes
print(f"Pickle serialized bytes: {pickle_len} bytes")
print(f"Difference (pickle_len - raw_nbytes): {diff} bytes")

print("\n=== PICKLE DISASSEMBLY (OPCODES) ===")
# Disassemble pickle bytecode to inspect exactly what the 161 bytes are
import io
out = io.StringIO()
pickletools.dis(pickled, out=out)
disassembly = out.getvalue()
print("\nFirst 30 lines of pickle disassembly:")
print("\n".join(disassembly.splitlines()[:30]))
print("\nLast 15 lines of pickle disassembly:")
print("\n".join(disassembly.splitlines()[-15:]))
