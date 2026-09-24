"""Load run CSVs, remove baseline, find and integrate peaks.

This is deliberately small.  For method-grade integration use OpenChrom (GUI) or
hplc-py (``pip install hplc-py``); see docs/plan.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.signal import find_peaks, peak_widths
from scipy.sparse.linalg import spsolve


def load_run(path: str | Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return the sample table and the ``# key: value`` metadata from a run CSV."""
    meta: dict[str, str] = {}
    with open(path) as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            body = line[1:].strip()
            if ":" in body:
                k, v = body.split(":", 1)
                meta[k.strip()] = v.strip()
    df = pd.read_csv(path, comment="#")
    return df, meta


def als_baseline(y: np.ndarray, lam: float = 1e10, p: float = 0.001, n_iter: int = 10) -> np.ndarray:
    """Asymmetric least squares baseline (Eilers & Boelens 2005).

    ``lam`` scales with the fourth power of samples-per-peak; 1e10 suits 20 Hz HPLC data
    (peaks 60-400 points wide).  Lower it for sparser traces.
    """
    y = np.asarray(y, dtype=float)
    n = y.size
    d = sparse.diags([1.0, -2.0, 1.0], [0, -1, -2], shape=(n, n - 2))
    dtd = lam * (d @ d.T)
    w = np.ones(n)
    z = y
    for _ in range(n_iter):
        wmat = sparse.spdiags(w, 0, n, n)
        z = spsolve((wmat + dtd).tocsc(), w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return np.asarray(z)


@dataclass
class Peak:
    rt_s: float
    height: float
    area: float
    width_s: float
    start_s: float
    end_s: float


def integrate(
    t: np.ndarray,
    y: np.ndarray,
    min_height: float | None = None,
    min_width_s: float = 1.0,
    subtract_baseline: bool = True,
) -> list[Peak]:
    """Find peaks in ``y(t)`` and integrate each between its half-prominence bounds."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if subtract_baseline:
        y = y - als_baseline(y)
    dt = float(np.median(np.diff(t)))
    if min_height is None:
        noise = 1.4826 * np.median(np.abs(y - np.median(y)))
        min_height = max(10 * noise, 1e-12)
    idx, props = find_peaks(y, height=min_height, width=max(1, min_width_s / dt), prominence=min_height)
    if idx.size == 0:
        return []
    # Integrate between the points where the peak has dropped to ~0.5% of prominence.
    _, _, left, right = peak_widths(y, idx, rel_height=0.995)
    peaks = []
    for i, li, ri in zip(idx, left, right):
        a, b = int(np.floor(li)), int(np.ceil(ri)) + 1
        area = float(np.trapezoid(y[a:b], t[a:b]))
        w = float(peak_widths(y, [i], rel_height=0.5)[0][0] * dt)
        peaks.append(Peak(float(t[i]), float(y[i]), area, w, float(t[a]), float(t[min(b, len(t) - 1)])))
    return peaks


def peak_table(peaks: list[Peak]) -> pd.DataFrame:
    return pd.DataFrame([p.__dict__ for p in peaks])
