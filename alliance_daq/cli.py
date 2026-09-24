"""Command-line entry point: ``alliance-daq``."""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

from .channels import DEFAULT_MAP, ChannelMap
from .logger import RunLogger


class _VirtualClock:
    """Advances only when 'slept', so simulated runs finish instantly and deterministically."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def _build_adc(args):
    if args.simulate:
        from .adc import SimulatedAdc

        clock = _VirtualClock()
        args._clock = clock
        return SimulatedAdc(clock=clock)
    from .adc import ADS1263Adc

    return ADS1263Adc(adc_rate_sps=args.adc_rate)


def _build_trigger(args):
    from . import trigger as trg

    if args.simulate and args.trigger == "gpio":
        return trg.TimedTrigger(2.0)
    if args.trigger == "gpio":
        return trg.GpioTrigger(args.trigger_pin)
    if args.trigger == "key":
        return trg.KeyboardTrigger()
    return trg.ImmediateTrigger()


def cmd_record(args) -> int:
    channels = ChannelMap.load(args.channels) if args.channels else DEFAULT_MAP
    adc = _build_adc(args)
    trigger = _build_trigger(args)
    clock = getattr(args, "_clock", None)
    logger = RunLogger(adc, channels, rate_hz=args.rate, out_dir=args.out, **({"clock": clock, "sleep": clock.sleep} if clock else {}))

    def _stop(*_):
        logger.stop_requested = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        n = 0
        while True:
            n += 1
            label = args.label if args.count == 1 else f"{args.label}-{n:03d}"
            print(f"[{label}] waiting for trigger ({args.trigger})...", flush=True)
            res = logger.run_triggered(trigger, args.duration, label, timeout_s=args.timeout)
            if res is None:
                print("trigger timed out", file=sys.stderr)
                return 2
            print(f"[{label}] wrote {res.path} ({res.samples} samples, {res.duration_s:.1f} s)", flush=True)
            if logger.stop_requested or (args.count and n >= args.count):
                return 0
    finally:
        trigger.close()
        adc.close()


def cmd_live(args) -> int:
    """Print scaled channel values continuously.  Use it to check wiring and offsets."""
    import time

    channels = ChannelMap.load(args.channels) if args.channels else DEFAULT_MAP
    adc = _build_adc(args)
    if hasattr(adc, "start_run"):
        adc.start_run()
    try:
        while True:
            volts = adc.read(channels.adc_channels)
            print("  ".join(f"{c.name}={c.scale(v):+.6f} {c.unit}" for c, v in zip(channels.channels, volts)), flush=True)
            time.sleep(1.0 / args.rate)
    except KeyboardInterrupt:
        return 0
    finally:
        adc.close()


def cmd_peaks(args) -> int:
    from .analysis import integrate, load_run, peak_table

    df, meta = load_run(args.csv)
    col = args.column or df.columns[1]
    peaks = integrate(df["time_s"].to_numpy(), df[col].to_numpy(), min_height=args.min_height)
    print(f"# {Path(args.csv).name}  column={col}  started={meta.get('started', '?')}")
    if not peaks:
        print("no peaks found")
        return 1
    print(peak_table(peaks).to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    return 0


def cmd_quant(args) -> int:
    from .analysis import load_run
    from .quant import quantify, save_fit_figure

    df, meta = load_run(args.csv)
    col = args.column or df.columns[1]
    known = [float(x) for x in args.known.split(",")] if args.known else None
    peaks, chrom = quantify(df, col, prominence=args.prominence, baseline_window_min=args.baseline_window, known_peaks_s=known)
    src = Path(args.csv)
    out = Path(args.out) if args.out else src.with_name(src.stem + f"_{col}_peaks.csv")
    peaks.to_csv(out, index=False, float_format="%.6g")
    print(f"# {src.name}  column={col}  started={meta.get('started', '?')}  peaks={len(peaks)}  -> {out}")
    print(peaks.to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    if args.plot:
        fig = save_fit_figure(chrom, args.plot)
        print(f"# figure -> {fig}")
    return 0 if len(peaks) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="alliance-daq", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--simulate", action="store_true", help="use the synthetic ADC (no hardware)")
    common.add_argument("--channels", help="TOML channel map (default: built-in uv1/uv2/els/pressure)")
    common.add_argument("--rate", type=float, default=20.0, help="samples per second per channel (default 20)")
    common.add_argument("--adc-rate", type=float, default=400, help="ADS1263 internal rate in SPS (default 400)")

    r = sub.add_parser("record", parents=[common], help="wait for trigger, record a run to CSV")
    r.add_argument("--duration", type=float, required=True, help="run length in seconds")
    r.add_argument("--label", default="run")
    r.add_argument("--out", default="runs")
    r.add_argument("--trigger", choices=["gpio", "key", "now"], default="gpio")
    r.add_argument("--trigger-pin", type=int, default=25, help="BCM pin wired to e2695 Inject Start (default 25)")
    r.add_argument("--timeout", type=float, default=None, help="give up waiting for the trigger after N s")
    r.add_argument("--count", type=int, default=1, help="number of runs to record, 0 = until Ctrl-C")
    r.set_defaults(func=cmd_record)

    l = sub.add_parser("live", parents=[common], help="print live channel values")
    l.set_defaults(func=cmd_live)

    k = sub.add_parser("peaks", help="quick-look peak integration (SciPy only, no extra deps)")
    k.add_argument("csv")
    k.add_argument("--column", help="signal column (default: first channel)")
    k.add_argument("--min-height", type=float, default=None)
    k.set_defaults(func=cmd_peaks)

    q = sub.add_parser("quant", help="fit and quantify peaks with hplc-py (needs the [analysis] extra)")
    q.add_argument("csv")
    q.add_argument("--column", help="signal column (default: first channel)")
    q.add_argument("--prominence", type=float, default=0.01, help="min peak prominence relative to the tallest peak (default 0.01)")
    q.add_argument("--baseline-window", type=float, default=1.0, help="baseline correction window in minutes (default 1.0)")
    q.add_argument("--known", help="comma-separated retention times in seconds to seed the fit")
    q.add_argument("--out", help="peak table CSV (default: <run>_<column>_peaks.csv next to the run)")
    q.add_argument("--plot", help="save hplc-py's fit figure to this PNG path")
    q.set_defaults(func=cmd_quant)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
