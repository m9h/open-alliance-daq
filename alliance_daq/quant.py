"""Method-grade peak quantification with hplc-py (Chure & Cremer, JOSS 2024).

hplc-py fits a mixture of skew-normal peaks to the signal, so overlapping peaks are
resolved rather than split at a valley.  It is the project's primary quantification
engine; :mod:`alliance_daq.analysis` is the quick-look fallback that needs only SciPy.

Install with ``pip install 'open-alliance-daq[analysis]'``.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import numpy as np
import pandas as pd


def _chromatogram(df: pd.DataFrame, column: str):
    try:
        from hplc.quant import Chromatogram
    except ImportError as e:  # pragma: no cover
        raise ImportError("hplc-py is not installed; run: pip install 'open-alliance-daq[analysis]'") from e
    work = pd.DataFrame({"time_min": df["time_s"].to_numpy() / 60.0, "signal": df[column].to_numpy()})
    return Chromatogram(work, cols={"time": "time_min", "signal": "signal"})


def quantify(
    df: pd.DataFrame,
    column: str,
    prominence: float = 0.01,
    baseline_window_min: float = 1.0,
    known_peaks_s: list[float] | None = None,
    verbose: bool = False,
):
    """Fit peaks in ``df[column]`` and return ``(peaks, chromatogram)``.

    ``peaks`` columns: rt_s, amplitude, width_s (skew-normal scale), skew, area.
    Area is converted from hplc-py's per-sample sum to signal-units × seconds, so a
    detector at 1 V/AU gives AU·s directly.
    ``prominence`` is relative to the tallest peak (hplc-py convention).
    """
    chrom = _chromatogram(df, column)
    dt_s = float(np.median(np.diff(df["time_s"].to_numpy())))
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        chrom.correct_baseline(window=baseline_window_min, verbose=verbose)
        known = [rt / 60.0 for rt in known_peaks_s] if known_peaks_s else []
        fitted = chrom.fit_peaks(known_peaks=known, prominence=prominence)
    peaks = pd.DataFrame({
        "rt_s": fitted["retention_time"] * 60.0,
        "amplitude": fitted["amplitude"],
        "width_s": fitted["scale"] * 60.0,
        "skew": fitted["skew"],
        "area": fitted["area"] * dt_s,
    }).sort_values("rt_s").reset_index(drop=True)
    return peaks, chrom


def save_fit_figure(chrom, path: str | Path) -> Path:
    """Write hplc-py's reconstruction plot (signal, fitted peaks, sum) to ``path``."""
    import matplotlib

    matplotlib.use("Agg")
    fig, _ = chrom.show()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return Path(path)
