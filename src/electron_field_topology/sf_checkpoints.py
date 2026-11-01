"""Atomic, lossless checkpoints for bounded static continuation. Apache-2.0."""
import hashlib
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from .skyrme import NORTH, normalize, set_boundary


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp():
    now = datetime.now(timezone.utc)
    return {"utc": now.isoformat(), "melbourne": now.astimezone(ZoneInfo("Australia/Melbourne")).isoformat()}


def atomic_json(path, value):
    path = Path(path); temp = path.with_name(path.name+".tmp")
    with temp.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)


def checkpoint(path, field, h, q, iteration, elapsed, config_sha):
    path = Path(path); temp = path.with_name(path.name+".tmp")
    written = timestamp()
    with temp.open("wb") as f:
        np.savez_compressed(f, field=np.asarray(field, dtype=np.float64), h=float(h),
                            expected_q=q, model_id="SF-J2015-static", iteration=iteration,
                            elapsed_seconds=elapsed, config_sha256=config_sha,
                            written_utc=written['utc'], written_melbourne=written['melbourne'])
        f.flush(); os.fsync(f.fileno())
    if path.name == "latest.npz" and path.exists():
        os.replace(path, path.with_name("previous.npz"))
    os.replace(temp, path)


def load_field(path, n, h, expected_q):
    """Load old float32 or new float64 fields; reject wrong model/charge/bounds."""
    with np.load(path, allow_pickle=False) as data:
        u = data["field"].astype(float); oldh = float(data["h"])
        if "model_id" in data and str(data["model_id"]) != "SF-J2015-static":
            raise ValueError("Checkpoint model mismatch")
        if "expected_q" in data and int(data["expected_q"]) != expected_q:
            raise ValueError("Checkpoint Hopf-label mismatch")
    if (u.ndim != 4 or u.shape[-1] != 3 or len(set(u.shape[:3])) != 1
            or not np.isfinite(oldh) or oldh <= 0 or not np.isfinite(u).all()):
        raise ValueError("Invalid checkpoint dimensions/spacing/values")
    if np.max(abs(np.linalg.norm(u, axis=-1)-1)) > 1e-5:
        raise ValueError("Checkpoint is not a resolved unit-vector field")
    for axis in range(3):
        sl = [slice(None)]*4; sl[axis] = [0, 1, len(u)-2, len(u)-1]
        if np.max(abs(u[tuple(sl)]-NORTH)) > 1e-10:
            raise ValueError("Checkpoint fixed boundary mismatch")
    if u.shape != (n, n, n, 3) or oldh != h:
        axis = (np.arange(n)-(n-1)/2)*h/oldh+(len(u)-1)/2
        coords = np.array(np.meshgrid(axis, axis, axis, indexing="ij"))
        u = np.stack([map_coordinates(u[..., i], coords, order=1, mode="constant", cval=NORTH[i])
                      for i in range(3)], axis=-1)
    return set_boundary(normalize(u))
