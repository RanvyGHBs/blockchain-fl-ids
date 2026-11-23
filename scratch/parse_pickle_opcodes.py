import sys
import os
sys.path.insert(0, os.path.abspath("."))
import pickle
import pickletools
import numpy as np
import torch
from src.models.ids_net import IDSNet

model = IDSNet(input_dim=122, num_classes=2)

print("--- PARAMETERS TABLE ---")
total_params = 0
for name, param in model.named_parameters():
    count = param.numel()
    total_params += count
    print(f"| `{name}` | {list(param.shape)} | {count} | `{param.dtype}` | {param.numel() * param.element_size()} bytes |")
print(f"Total Trainable Parameters: {total_params} elements = {total_params * 4} bytes")

print("\n--- NON-TRAINABLE BUFFERS TABLE ---")
total_buffers = 0
for name, buf in model.named_buffers():
    count = buf.numel()
    total_buffers += count
    print(f"| `{name}` | {list(buf.shape)} | {count} | `{buf.dtype}` | {buf.numel() * buf.element_size()} bytes |")
print(f"Total Non-Trainable Buffers: {total_buffers} elements")

weights_vec = model.get_weights_vector()
pickled = pickle.dumps(weights_vec)

print(f"\nRaw float32 array nbytes: {weights_vec.nbytes} bytes")
print(f"Pickled array total bytes: {len(pickled)} bytes")
print(f"Pickle header & metadata overhead: {len(pickled) - weights_vec.nbytes} bytes")

print("\n--- PICKLE OPCODES BREAKDOWN ---")
ops = list(pickletools.genops(pickled))
total_accounted = 0
for op, arg, pos in ops:
    if op.name == "BYTEARRAY8":
        # The raw float32 payload
        payload_bytes = len(arg)
        print(f"At {pos:6d}: Opcode `{op.name}` -> Payload Buffer ({payload_bytes} bytes)")
    else:
        print(f"At {pos:6d}: Opcode `{op.name}` ({op.code!r}) -> Arg: {arg!r}")
