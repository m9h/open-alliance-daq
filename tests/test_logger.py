import itertools

from alliance_daq.adc import SimulatedAdc
from alliance_daq.analysis import integrate, load_run
from alliance_daq.channels import DEFAULT_MAP, ChannelMap
from alliance_daq.logger import RunLogger
from alliance_daq.trigger import ImmediateTrigger


class FakeClock:
    """Deterministic clock: every call advances by `step` seconds. Sleep is a no-op."""

    def __init__(self, step=0.0):
        self.t = 0.0
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t

    def sleep(self, s):
        self.t += s


def test_record_writes_expected_shape(tmp_path):
    clock = FakeClock()
    adc = SimulatedAdc(noise_v=0.0, clock=clock)
    logger = RunLogger(adc, DEFAULT_MAP, rate_hz=20, out_dir=tmp_path, clock=clock, sleep=clock.sleep)
    res = logger.run_triggered(ImmediateTrigger(), duration_s=200.0, label="t-1")
    assert res.samples == 4000
    df, meta = load_run(res.path)
    assert list(df.columns) == ["time_s", "uv1", "uv2", "els", "pressure"]
    assert len(df) == 4000
    assert meta["rate_hz"] == "20"
    assert meta["label"] == "t-1"
    assert abs(df["time_s"].iloc[-1] - 3999 / 20) < 1e-6


def test_simulated_peaks_are_recovered(tmp_path):
    clock = FakeClock()
    adc = SimulatedAdc(noise_v=20e-6, clock=clock)
    logger = RunLogger(adc, DEFAULT_MAP, rate_hz=20, out_dir=tmp_path, clock=clock, sleep=clock.sleep)
    res = logger.run_triggered(ImmediateTrigger(), duration_s=200.0)
    df, _ = load_run(res.path)
    peaks = integrate(df["time_s"].to_numpy(), df["uv1"].to_numpy())
    rts = sorted(p.rt_s for p in peaks)
    assert len(rts) == 3
    for found, (rt, height, sigma) in zip(rts, SimulatedAdc.PEAKS):
        assert abs(found - rt) < 0.5
    # Gaussian area = h * sigma * sqrt(2 pi); allow 5 %
    import math

    for p, (rt, h, s) in zip(sorted(peaks, key=lambda p: p.rt_s), SimulatedAdc.PEAKS):
        assert abs(p.area - h * s * math.sqrt(2 * math.pi)) / (h * s * math.sqrt(2 * math.pi)) < 0.05


def test_channel_map_scaling_and_validation(tmp_path):
    toml = tmp_path / "ch.toml"
    toml.write_text(
        '[[channel]]\nname="a"\nadc_channel=0\nvolts_per_unit=2.0\nunit="AU"\n'
        '[[channel]]\nname="b"\nadc_channel=3\nvolts_per_unit=0.0004\nunit="psi"\n'
    )
    cm = ChannelMap.load(toml)
    assert cm.names == ["a", "b"]
    assert cm.channels[0].scale(1.0) == 0.5
    assert abs(cm.channels[1].scale(2.0) - 5000.0) < 1e-9
    toml.write_text('[[channel]]\nname="a"\nadc_channel=0\n[[channel]]\nname="b"\nadc_channel=0\n')
    try:
        ChannelMap.load(toml)
    except ValueError as e:
        assert "twice" in str(e)
    else:
        raise AssertionError("duplicate adc_channel should fail")


def test_stop_request_ends_run_early(tmp_path):
    clock = FakeClock()
    adc = SimulatedAdc(noise_v=0.0, clock=clock)
    logger = RunLogger(adc, DEFAULT_MAP, rate_hz=10, out_dir=tmp_path, clock=clock, sleep=clock.sleep)
    counter = itertools.count()

    def read(chs, _orig=adc.read):
        if next(counter) == 50:
            logger.stop_requested = True
        return _orig(chs)

    adc.read = read
    res = logger.record(duration_s=100.0)
    assert res.samples == 51


def test_ads1263_raw_conversion():
    from alliance_daq.adc import ADS1263Adc

    assert ADS1263Adc._raw_to_volts(0x7FFFFFFF) == 2.5
    assert abs(ADS1263Adc._raw_to_volts(0x80000000) + 2.5) < 1e-6
    assert ADS1263Adc._raw_to_volts(0) == 0.0


def test_hplcpy_quant_matches_simulator(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("hplc")
    import math

    from alliance_daq.quant import quantify

    clock = FakeClock()
    adc = SimulatedAdc(noise_v=20e-6, clock=clock)
    logger = RunLogger(adc, DEFAULT_MAP, rate_hz=20, out_dir=tmp_path, clock=clock, sleep=clock.sleep)
    res = logger.run_triggered(ImmediateTrigger(), duration_s=200.0)
    df, _ = load_run(res.path)
    peaks, _ = quantify(df, "uv1", prominence=0.02)
    assert len(peaks) == 3
    for (_, row), (rt, h, s) in zip(peaks.iterrows(), SimulatedAdc.PEAKS):
        assert abs(row.rt_s - rt) < 0.5
        true_area = h * s * math.sqrt(2 * math.pi)
        assert abs(row.area - true_area) / true_area < 0.05


def test_report_builds_tex_and_pdf(tmp_path):
    pytest = __import__("pytest")
    pytest.importorskip("hplc")
    pytest.importorskip("jinja2")
    import shutil

    from alliance_daq.report import build_report

    clock = FakeClock()
    adc = SimulatedAdc(noise_v=20e-6, clock=clock)
    logger = RunLogger(adc, DEFAULT_MAP, rate_hz=20, out_dir=tmp_path, clock=clock, sleep=clock.sleep)
    res = logger.run_triggered(ImmediateTrigger(), duration_s=200.0, label="rep")
    out = build_report([res.path], tmp_path / "report.pdf", columns=["uv1", "uv2"], prominence=0.02)
    tex = out["tex"].read_text()
    assert r"\section{Run" in tex and "uv1" in tex and "uv2" in tex
    assert tex.count(r"\begin{table}") == 2
    assert (tmp_path / "report_figs").exists()
    if shutil.which("tectonic") or shutil.which("latexmk"):
        assert out["pdf"] is not None and out["pdf"].stat().st_size > 10_000
