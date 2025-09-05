"""
Temporary helper script to run sensitivity analysis across multiple parameters in config.ini.

Usage (quick):
    python scripts\temp_sensitivity_runner.py

What it does:
 - Reads `config.ini` in repo root.
 - For each parameter name listed in `sensitivity_params` list below,
   it checks if a result file already exists under `results/sensitivity_runs/param_name.diff`.
 - If not present, it creates a temporary config file with the `sensitivity_analysis` section
   configured to vary that parameter across the range defined in the base config, then
   invokes the project's CLI entrypoint (`praxis_engine.main:backtest` via `run.py` or `python -m praxis_engine.main`) to run `sensitivity_analysis` command.
 - Captures the generated `results/sensitivity_analysis_report.md` and saves it as a per-param file.
 - Produces a simple diff against a baseline (if available) and writes a `.diff` file.

Notes:
 - This is intentionally simple and temporary.
 - Adjust `PY_CMD` if you need a specific python executable.
 - Designed for Windows cmd.exe.
"""
from configparser import ConfigParser
from pathlib import Path
import shutil
import subprocess
import datetime
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.ini"
RESULTS_DIR = ROOT / "results" / "sensitivity_runs"
TMP_CONFIG = ROOT / "config.tmp.ini"
PY_CMD = sys.executable  # Uses same python running this script

# List of parameter names to test. These should match the dotted names used by main.sensitivity_analysis
# Keep this small; add or remove params as you like. This script will look for the parameter in the
# [sensitivity_analysis] section to get start/end/step, but will override parameter_to_vary for each run.
SENSITIVITY_PARAMS = [
    "strategy_params.bb_length",
    "strategy_params.rsi_length",
    "strategy_params.hurst_length",
    "strategy_params.exit_days",
    "strategy_params.min_history_days",
    "strategy_params.liquidity_lookback_days",
    "exit_logic.atr_period",
    "exit_logic.max_holding_days",
]


def parse_range_string(s: str, global_step: float | None = None):
    """Parse a string like 'start,end,step' or 'start,end' and return (start, end, step).
    If only two values are present, step falls back to global_step.
    Returns floats; casting to int handled elsewhere when needed.
    """
    parts = [p.strip() for p in s.split(',') if p.strip()]
    if not parts:
        raise ValueError("Empty range string")
    if len(parts) == 1:
        raise ValueError("Range must have at least start and end")
    start = float(parts[0])
    end = float(parts[1])
    if len(parts) >= 3 and parts[2] != "":
        step = float(parts[2])
    else:
        if global_step is None:
            raise ValueError("No step provided and no global step to fall back to")
        step = float(global_step)

    if step == 0:
        raise ValueError("step cannot be zero")

    # Normalize step to positive and use sign inferred from start/end
    step = abs(step)
    if start > end:
        step = -step

    return start, end, step


def generate_sequence(start: float, end: float, step: float):
    """Yield values from start to end inclusive using step. Handles positive/negative steps."""
    vals = []
    v = start
    if step > 0:
        while v <= end + 1e-12:
            vals.append(v)
            v += step
    else:
        while v >= end - 1e-12:
            vals.append(v)
            v += step
    return vals


def is_base_param_int(base_cfg: ConfigParser, dotted_param: str) -> bool:
    """Check base config for whether the parameter is defined and looks like an int."""
    # dotted_param like 'strategy_params.rsi_length' -> section 'strategy_params', option 'rsi_length'
    try:
        section, option = dotted_param.split('.', 1)
    except ValueError:
        return False
    if section in base_cfg and option in base_cfg[section]:
        v = base_cfg[section][option].strip().strip('"')
        try:
            int(v)
            return True
        except Exception:
            return False
    return False


def ensure_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def read_config(path: Path) -> ConfigParser:
    cp = ConfigParser()
    cp.read(path, encoding="utf-8")
    return cp


def write_config(cp: ConfigParser, path: Path):
    with path.open("w", encoding="utf-8") as f:
        cp.write(f)


def run_sensitivity_with_config(tmp_cfg_path: Path) -> Path:
    """Run the CLI sensitivity_analysis command using the provided config file path.
    Returns the path to the generated sensitivity report (if created).
    """
    # Invoke the Typer app via the package module so multiprocessing spawn/import works on Windows.
    # Use: python -m praxis_engine.main sensitivity-analysis --config config.tmp.ini
    cmd = [PY_CMD, "-m", "praxis_engine.main", "sensitivity-analysis", "--config", str(tmp_cfg_path)]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        print("Command failed:", proc.stderr)
        raise SystemExit(proc.returncode)

    # Expected output file
    out_path = ROOT / "results" / "sensitivity_analysis_report.md"
    if out_path.exists():
        # copy to a unique file and return path
        dest = tmp_cfg_path.stem + "_sensitivity_report.md"
        dest_path = RESULTS_DIR / dest
        shutil.copy2(out_path, dest_path)
        return dest_path
    return None


def simple_diff(a: Path, b: Path) -> str:
    # very small diff: line-by-line markers
    if not a.exists() or not b.exists():
        return ""
    a_lines = a.read_text(encoding="utf-8").splitlines()
    b_lines = b.read_text(encoding="utf-8").splitlines()
    out = []
    maxl = max(len(a_lines), len(b_lines))
    for i in range(maxl):
        la = a_lines[i] if i < len(a_lines) else ""
        lb = b_lines[i] if i < len(b_lines) else ""
        if la != lb:
            out.append(f"- {la}")
            out.append(f"+ {lb}")
    return "\n".join(out)


def main():
    ensure_dirs()

    base_cfg = read_config(CONFIG_PATH)
    # Read global sensitivity params
    if "sensitivity_analysis" not in base_cfg:
        print("No [sensitivity_analysis] in config.ini; aborting")
        return
    global_start = float(base_cfg["sensitivity_analysis"].get("start_value", 0))
    global_end = float(base_cfg["sensitivity_analysis"].get("end_value", 0))
    global_step = float(base_cfg["sensitivity_analysis"].get("step_size", 0))

    # Read per-parameter ranges if provided
    ranges_cfg = {}
    if "sensitivity_ranges" in base_cfg:
        for k, v in base_cfg["sensitivity_ranges"].items():
            ranges_cfg[k.strip()] = v.strip()

    # baseline file (if exists)
    baseline = RESULTS_DIR / "baseline_sensitivity.md"

    # If baseline not present, run once with default config to produce baseline
    if not baseline.exists():
        print("Baseline sensitivity report not found; generating baseline using current config.ini")
        try:
            tmp_name = f"baseline_{uuid.uuid4().hex}.tmp.ini"
            shutil.copy2(CONFIG_PATH, ROOT / tmp_name)
            r = run_sensitivity_with_config(ROOT / tmp_name)
            if r:
                shutil.copy2(r, baseline)
            (ROOT / tmp_name).unlink()
        except Exception as e:
            print("Failed to create baseline:", e)
            return

    for param in SENSITIVITY_PARAMS:
        out_diff = RESULTS_DIR / f"{param.replace('.', '_')}.diff"
        out_report = RESULTS_DIR / f"{param.replace('.', '_')}_report.md"

        # If a per-param report already exists, skip running sensitivity for this param
        if out_report.exists():
            print(f"Skipping {param} — report already exists: {out_report.name}")
            continue

        print(f"Running sensitivity for parameter: {param}")

        # Modify config: set sensitivity_analysis.parameter_to_vary to param
        cp = ConfigParser()
        cp.read(CONFIG_PATH, encoding="utf-8")

        # Determine start/end/step for this param from [sensitivity_ranges] or fallback to global
        if param in ranges_cfg:
            try:
                start, end, step = parse_range_string(ranges_cfg[param], global_step=global_step)
            except Exception as e:
                print(f"Invalid range for {param} in [sensitivity_ranges]: {e} — falling back to global")
                start, end, step = global_start, global_end, global_step
        else:
            start, end, step = global_start, global_end, global_step

        # Cast samples to int if base config param is integer
        should_cast_int = is_base_param_int(base_cfg, param)

        # Build a small string representation for the sensitivity section so the CLI will pick up the parameter_to_vary
        cp["sensitivity_analysis"]["parameter_to_vary"] = param
        cp["sensitivity_analysis"]["start_value"] = str(int(start) if should_cast_int else start)
        cp["sensitivity_analysis"]["end_value"] = str(int(end) if should_cast_int else end)
        cp["sensitivity_analysis"]["step_size"] = str(int(step) if should_cast_int else step)

        tmp_cfg_path = TMP_CONFIG
        write_config(cp, tmp_cfg_path)

        try:
            report_path = run_sensitivity_with_config(tmp_cfg_path)
            if report_path:
                # move to canonical name
                shutil.move(str(report_path), out_report)
                diff_text = simple_diff(baseline, out_report)
                out_diff.write_text(diff_text, encoding="utf-8")
                print(f"Saved report: {out_report} and diff: {out_diff}")
            else:
                print(f"No report generated for {param}")
        except Exception as e:
            print(f"Error running sensitivity for {param}: {e}")

        if tmp_cfg_path.exists():
            tmp_cfg_path.unlink()

    print("All done. Results in:", RESULTS_DIR)


if __name__ == "__main__":
    main()
