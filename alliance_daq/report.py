"""PDF report: traces, hplc-py fits, and peak tables for one or more runs.

Pipeline: matplotlib figures (PDF) + Jinja2 -> LaTeX -> tectonic (or latexmk).  The .tex
and figures are always written, so the report can be edited by hand or rebuilt without
the Python stack; the PDF is compiled when a LaTeX engine is on PATH.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .analysis import load_run
from .quant import quantify

# Categorical slots, fixed order (validated light-surface palette).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK2, GRID, FILL = "#1a1a19", "#6b6a63", "#e5e5e3", "#9ec5f4"


def _style():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
        "axes.titlecolor": INK, "axes.titleweight": "semibold", "axes.titlesize": 9.5, "axes.titlelocation": "left",
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "legend.frameon": False, "pdf.fonttype": 42,
    })
    return plt


def trace_figure(df: pd.DataFrame, channels: list[dict], path: Path) -> Path:
    """Small multiples, one panel per channel on a shared time axis (no dual axes)."""
    plt = _style()
    n = len(channels)
    fig, axes = plt.subplots(n, 1, figsize=(6.5, 1.0 * n + 0.4), sharex=True, squeeze=False)
    t = df["time_s"].to_numpy() / 60.0
    for i, (ax, ch) in enumerate(zip(axes[:, 0], channels)):
        ax.plot(t, df[ch["name"]].to_numpy(), color=SERIES[i % len(SERIES)], lw=1.4)
        ax.set_title(f"{ch['name']}  ({ch['unit']})" + (f"  —  {ch['source']}" if ch.get("source") else ""))
        ax.margins(x=0)
    axes[-1, 0].set_xlabel("time (min)")
    fig.tight_layout(h_pad=1.2)
    fig.savefig(path)
    plt.close(fig)
    return path


def fit_figure(chrom, peaks: pd.DataFrame, column: str, unit: str, path: Path) -> Path:
    """Baseline-corrected signal, hplc-py mixture, shaded components, numbered apices."""
    plt = _style()
    t = chrom.df[chrom.time_col].to_numpy()
    ycol = chrom.int_col if chrom.int_col.endswith("_corrected") else f"{chrom.int_col}_corrected"
    y = chrom.df[ycol].to_numpy()
    comps = np.asarray(chrom.unmixed_chromatograms)
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    ax.plot(t, y, color=INK2, lw=1.0, label="signal (baseline corrected)")
    for k in range(comps.shape[1]):
        ax.fill_between(t, 0, comps[:, k], color=FILL, alpha=0.55, lw=0)
    ax.plot(t, comps.sum(axis=1), color=SERIES[0], lw=1.8, ls=(0, (4, 2)), label="fitted mixture")
    for i, row in peaks.iterrows():
        rt_min = float(row["rt_s"]) / 60.0
        ax.annotate(str(i + 1), (rt_min, float(np.interp(rt_min, t, y))),
                    textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8, color=INK)
    ax.set_title(f"{column}: hplc-py skew-normal fit")
    ax.set_xlabel("time (min)")
    ax.set_ylabel(unit)
    ax.margins(x=0)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


@dataclass
class RunSection:
    name: str
    meta: dict
    channels: list[dict]
    n_samples: int
    duration_s: float
    trace_fig: str
    fits: list[dict] = field(default_factory=list)  # {column, unit, fig, peaks(list of dict), n}


def _parse_channels(meta: dict) -> list[dict]:
    out = []
    for k, v in meta.items():
        if k.startswith("channel "):
            d = {"name": k.split(" ", 1)[1]}
            for tok in v.split():
                if "=" in tok:
                    kk, vv = tok.split("=", 1)
                    d[kk] = vv
            # 'source' may contain spaces: everything after 'source='
            if "source=" in v:
                d["source"] = v.split("source=", 1)[1]
            out.append(d)
    return out


def _tex_escape(s) -> str:
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    return s


def build_report(
    csv_paths: list[str | Path],
    out_pdf: str | Path,
    columns: list[str] | None = None,
    prominence: float = 0.01,
    baseline_window_min: float = 1.0,
    title: str = "HPLC run report",
    compile_pdf: bool = True,
) -> dict:
    """Write <out>.tex, figures, and (if a LaTeX engine is available) <out>.pdf.

    Returns {"tex": Path, "pdf": Path | None, "engine": str | None}.
    """
    out_pdf = Path(out_pdf)
    out_dir = out_pdf.parent
    figdir = out_dir / (out_pdf.stem + "_figs")
    figdir.mkdir(parents=True, exist_ok=True)
    sections: list[RunSection] = []
    for p in csv_paths:
        p = Path(p)
        df, meta = load_run(p)
        channels = _parse_channels(meta)
        chan_names = [c["name"] for c in channels] or [c for c in df.columns if c != "time_s"]
        if not channels:
            channels = [{"name": c, "unit": ""} for c in chan_names]
        stem = p.stem
        sec = RunSection(
            name=stem, meta=meta, channels=channels, n_samples=len(df),
            duration_s=float(df["time_s"].iloc[-1]) if len(df) else 0.0,
            trace_fig=str(trace_figure(df, channels, figdir / f"{stem}_traces.pdf").relative_to(out_dir)),
        )
        cols = columns or [chan_names[0]]
        for col in cols:
            if col not in df.columns:
                continue
            unit = next((c.get("unit", "") for c in channels if c["name"] == col), "")
            peaks, chrom = quantify(df, col, prominence=prominence, baseline_window_min=baseline_window_min)
            fig = fit_figure(chrom, peaks, col, unit, figdir / f"{stem}_{col}_fit.pdf")
            total = float(peaks["area"].sum()) if len(peaks) else 0.0
            sec.fits.append({
                "column": col, "unit": unit, "fig": str(fig.relative_to(out_dir)), "n": len(peaks),
                "peaks": [
                    {"i": i + 1, "rt_s": float(r["rt_s"]), "rt_min": float(r["rt_s"]) / 60.0,
                     "amplitude": float(r["amplitude"]), "width_s": float(r["width_s"]),
                     "skew": float(r["skew"]), "area": float(r["area"]),
                     "pct": 100.0 * float(r["area"]) / total if total else 0.0}
                    for i, r in peaks.iterrows()
                ],
            })
        sections.append(sec)

    from jinja2 import Environment, PackageLoader

    env = Environment(
        loader=PackageLoader("alliance_daq", "templates"),
        block_start_string=r"\BLOCK{", block_end_string="}",
        variable_start_string=r"\VAR{", variable_end_string="}",
        comment_start_string=r"\#{", comment_end_string="}",
        autoescape=False, trim_blocks=True, lstrip_blocks=True,
    )
    env.filters["tex"] = _tex_escape
    tex = env.get_template("report.tex.j2").render(
        title=title, generated=dt.datetime.now().strftime("%Y-%m-%d %H:%M"), version=__version__,
        sections=sections, prominence=prominence, baseline_window_min=baseline_window_min,
    )
    tex_path = out_pdf.with_suffix(".tex")
    tex_path.write_text(tex)
    result = {"tex": tex_path, "pdf": None, "engine": None}
    if compile_pdf:
        engine = _compile(tex_path)
        if engine:
            result["pdf"], result["engine"] = tex_path.with_suffix(".pdf"), engine
    return result


def _compile(tex_path: Path) -> str | None:
    if shutil.which("tectonic"):
        cmd = ["tectonic", "--keep-logs", "-o", str(tex_path.parent), str(tex_path)]
        engine = "tectonic"
    elif shutil.which("latexmk"):
        cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", f"-output-directory={tex_path.parent}", str(tex_path)]
        engine = "latexmk"
    else:
        return None
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=tex_path.parent)
    if proc.returncode != 0:
        raise RuntimeError(f"{engine} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return engine
