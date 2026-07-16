# analyzer.py
import hashlib
import math
import os
from enum import Enum

class Verdict(Enum):
    CLEAN = 1
    SUSPICIOUS = 2
    MALICIOUS = 3

ENTROPY_THRESHOLD = 7.5      # tweak in experiments
MIN_SIZE_FOR_ENTROPY = 1024  # bytes

def sha256sum(path, blocksize=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(blocksize), b""):
            h.update(chunk)
    return h.hexdigest()

def file_entropy(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) == 0:
        return 0.0
    freqs = [0] * 256
    for b in data:
        freqs[b] += 1
    entropy = 0.0
    for count in freqs:
        if count == 0:
            continue
        p = count / len(data)
        entropy -= p * math.log2(p)
    return entropy


def basic_name_rule(path):
    name = os.path.basename(path).lower()
    # simple example rule: ransom-like extension
    suspicious_ext = [".locked", ".encrypted", ".crypt", ".pay"]
    return any(name.endswith(ext) for ext in suspicious_ext)

def analyze_file(path) -> Verdict:
    try:
        size = os.path.getsize(path)
    except FileNotFoundError:
        return Verdict.SUSPICIOUS

    # hash is computed but mainly for logging / DB
    _hash = sha256sum(path)

    score = 0
    if size > MIN_SIZE_FOR_ENTROPY:
        ent = file_entropy(path)
        if ent > ENTROPY_THRESHOLD:
            score += 1

    if basic_name_rule(path):
        score += 2

    if score >= 3:
        return Verdict.MALICIOUS
    elif score >= 1:
        return Verdict.SUSPICIOUS
    else:
        return Verdict.CLEAN
