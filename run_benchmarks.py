#!/bin/sh
''':'
exec python3 "$0" "$@"
':'''

import argparse
import csv
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VESTA_BIN = ROOT / "target/release/vesta-benchmark"
SUBS2SRS_DLL = ROOT / "subs2srs_source/subs2srs/bin/Release/net10.0/subs2srs.dll"
OUTPUT_DIR = Path("/tmp/benchmarks_out")
CSV_PATH = ROOT / "benchmarks_result.csv"
LOG_PATH = ROOT / "benchmarks_run.log"
CSV_FIELDS = ["fixture", "subs2srs_ms", "vesta_tsv_ms", "vesta_apkg_ms"]
BENCHMARKS = [
    ("subs2srs_ms", "subs2srs headless adapter", lambda fixture: run_subs2srs(fixture)),
    ("vesta_tsv_ms", "Vesta TSV", lambda fixture: run_vesta(fixture, "tsv")),
    ("vesta_apkg_ms", "Vesta APKG", lambda fixture: run_vesta(fixture, "apkg")),
]


def log(message: str, *, console: bool = False) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    if console:
        print(message, flush=True)


def console(message: str) -> None:
    print(message, flush=True)


PLOT_LABELS = {
    "detour": "Detour\nfull film",
    "interstellar": "Interstellar\nfull film",
    "trainspotting": "Trainspotting\nfull film",
    "uncut_gems": "Uncut Gems\nfull film",
    "zootopia": "Zootopia\nfull film",
}
PLOT_ORDER = [
    "detour",
    "trainspotting",
    "uncut_gems",
    "interstellar",
    "zootopia",
]


@dataclass(frozen=True)
class Fixture:
    name: str
    target_subs: Path
    native_subs: Path
    video: Path


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".flv", ".ogm", ".vob"}


def normalize_movie_key(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"\([^)]*\)", " ", stem)
    stem = re.sub(r"\[[^\]]*\]", " ", stem)
    stem = re.sub(r"\b(?:19|20)\d{2}\b", " ", stem)
    stem = re.sub(
        r"\b(?:720p|1080p|2160p|4k|bluray|brrip|webrip|web-dl|webdl|hdtv|dvdrip|x264|x265|h264|h265|yify|yts|ag|bokutox|aac|dts|eng)\b",
        " ",
        stem,
    )
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    return re.sub(r"_+", "_", stem).strip("_")


def fixture_name_from_key(key: str) -> str:
    return key or "movie"


def discover_fixtures() -> list[Fixture]:
    test_subs = ROOT / "Test_Subs"
    if not test_subs.exists():
        return []

    target_subs: dict[str, Path] = {}
    native_subs: dict[str, Path] = {}
    videos: dict[str, Path] = {}

    for path in sorted(test_subs.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".srt":
            match = re.match(r"(.+)-([a-z]{2}(?:-[a-z]{2})?)$", path.stem, re.IGNORECASE)
            if not match:
                continue
            key = normalize_movie_key(match.group(1))
            lang = match.group(2).lower()
            if lang == "en":
                target_subs[key] = path
            elif lang == "it":
                native_subs[key] = path
        elif suffix in VIDEO_EXTENSIONS:
            videos[normalize_movie_key(path.name)] = path

    fixtures = []
    for key, target in sorted(target_subs.items()):
        native = native_subs.get(key)
        video = videos.get(key)
        if native and video:
            fixtures.append(
                Fixture(
                    name=fixture_name_from_key(key),
                    target_subs=target,
                    native_subs=native,
                    video=video,
                )
            )
    return fixtures


FIXTURES = discover_fixtures()


def parse_reported_ms(output: str, prefix: str) -> float | None:
    match = re.search(rf"{re.escape(prefix)}:\s*(\d+(?:\.\d+)?)\s*ms", output)
    return float(match.group(1)) if match else None


def safe_log_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "command"


def run_with_heartbeat(cmd: list[str], label: str, cwd: Path | None = None) -> tuple[subprocess.CompletedProcess[str], float]:
    log(f"[start] {label}")
    log(f"[command] {' '.join(cmd)}")
    command_log_dir = OUTPUT_DIR / "logs"
    command_log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = command_log_dir / f"{safe_log_name(label)}.stdout.log"
    stderr_path = command_log_dir / f"{safe_log_name(label)}.stderr.log"
    start_time = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
        )

        while True:
            try:
                process.wait(timeout=60)
                break
            except subprocess.TimeoutExpired:
                elapsed_s = time.perf_counter() - start_time
                log(f"[running] {label} - {elapsed_s:.0f}s elapsed")

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
    log(f"[stdout] {label}: {stdout_path}")
    log(f"[stderr] {label}: {stderr_path}")
    log(f"[done] {label} - {elapsed_ms / 1000:.1f}s")
    return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr), elapsed_ms


def clean_output_dir(tool: str, fixture: Fixture, export_fmt: str | None = None) -> Path:
    parts = [tool]
    if export_fmt:
        parts.append(export_fmt)
    parts.append(fixture.name)
    out_dir = OUTPUT_DIR / "_".join(parts)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def ensure_inputs_exist(fixture: Fixture) -> None:
    missing = [
        path for path in (fixture.target_subs, fixture.native_subs, fixture.video)
        if not path.exists()
    ]
    if missing:
        joined = "\n  ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Fixture {fixture.name} is missing:\n  {joined}")


def run_subs2srs(fixture: Fixture) -> float | None:
    log(f"Running subs2srs headless adapter for {fixture.name}...")
    out_dir = clean_output_dir("subs2srs", fixture)
    cmd = [
        "dotnet",
        str(SUBS2SRS_DLL),
        "--cli",
        str(fixture.target_subs),
        str(fixture.native_subs),
        str(fixture.video),
        str(out_dir),
    ]

    result, elapsed_ms = run_with_heartbeat(cmd, f"subs2srs {fixture.name}")

    if result.returncode != 0:
        log(f"subs2srs failed for {fixture.name}:\n{result.stderr or result.stdout}", console=True)
        return None

    measured = parse_reported_ms(result.stdout, "SUBS2SRS_BENCHMARK_SUCCESS") or elapsed_ms
    log(f"[result] subs2srs {fixture.name}: {measured / 1000:.3f}s")
    return measured


def run_vesta(fixture: Fixture, export_fmt: str) -> float | None:
    log(f"Running Vesta core ({export_fmt}) for {fixture.name}...")
    out_dir = clean_output_dir("vesta", fixture, export_fmt)
    cmd = [
        str(VESTA_BIN),
        str(fixture.target_subs),
        str(fixture.native_subs),
        str(fixture.video),
        str(out_dir),
        export_fmt,
    ]

    result, elapsed_ms = run_with_heartbeat(cmd, f"Vesta {export_fmt} {fixture.name}")

    if result.returncode != 0:
        log(f"Vesta failed for {fixture.name}:\n{result.stderr or result.stdout}", console=True)
        return None

    measured = parse_reported_ms(result.stdout, "VESTA_BENCHMARK_SUCCESS") or elapsed_ms
    log(f"[result] Vesta {export_fmt} {fixture.name}: {measured / 1000:.3f}s")
    return measured


def ensure_binaries() -> None:
    console("Compilazione benchmark...")
    log("Compiling Vesta benchmark binary in release mode...")
    result, _ = run_with_heartbeat(
        ["cargo", "build", "--release", "--package", "vesta", "--bin", "vesta-benchmark"],
        "Vesta benchmark release build",
        cwd=ROOT,
    )
    if result.returncode != 0:
        log(result.stdout)
        log(result.stderr, console=True)
        raise subprocess.CalledProcessError(result.returncode, result.args)

    log("Compiling subs2srs headless adapter in release mode...")
    result, _ = run_with_heartbeat(
        ["dotnet", "build", "subs2srs_source/subs2srs/subs2srs.csproj", "-c", "Release"],
        "subs2srs release build",
        cwd=ROOT,
    )
    if result.returncode != 0:
        log(result.stdout)
        log(result.stderr, console=True)
        raise subprocess.CalledProcessError(result.returncode, result.args)


def is_missing(value: str | float | int | None) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    try:
        return float(value) <= 0
    except (TypeError, ValueError):
        return True


def default_row(fixture_name: str) -> dict[str, str]:
    return {"fixture": fixture_name, "subs2srs_ms": "", "vesta_tsv_ms": "", "vesta_apkg_ms": ""}


def load_results() -> dict[str, dict[str, str]]:
    if not CSV_PATH.exists():
        return {}

    known_fixtures = {fixture.name for fixture in FIXTURES}
    rows = {}
    with CSV_PATH.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fixture = row.get("fixture")
            if not fixture or fixture not in known_fixtures:
                continue
            normalized = default_row(fixture)
            normalized.update({field: row.get(field, "") for field in CSV_FIELDS})
            rows[fixture] = normalized
    return rows


def write_results(rows: dict[str, dict[str, str]], fixture_order: list[str]) -> None:
    ordered_names = [name for name in fixture_order if name in rows]
    ordered_names.extend(name for name in sorted(rows) if name not in ordered_names)

    with CSV_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for name in ordered_names:
            writer.writerow({field: rows[name].get(field, "") for field in CSV_FIELDS})


def format_ms(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def perform_benchmarks(selected: set[str] | None = None, reset: bool = False) -> None:
    LOG_PATH.write_text("", encoding="utf-8")
    ensure_binaries()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fixtures = [fixture for fixture in FIXTURES if selected is None or fixture.name in selected]
    unknown = selected - {fixture.name for fixture in FIXTURES} if selected else set()
    if unknown:
        raise ValueError(f"Unknown fixtures: {', '.join(sorted(unknown))}")

    fixture_order = [fixture.name for fixture in fixtures]
    results = {} if reset else load_results()
    if reset:
        write_results(results, fixture_order)

    console(f"Benchmark: {len(fixtures)} fixture x {len(BENCHMARKS)} misure. Log: {LOG_PATH}")
    for fixture in fixtures:
        ensure_inputs_exist(fixture)
        row = results.setdefault(fixture.name, default_row(fixture.name))
        fixture_values = []

        for field, label, runner in BENCHMARKS:
            if not reset and not is_missing(row.get(field)):
                log(f"Skipping {label} for {fixture.name}; already present in {CSV_PATH.name}.")
                fixture_values.append(f"{field.removesuffix('_ms')}={float(row[field]) / 1000:.3f}s")
                continue

            elapsed_ms = runner(fixture)
            row[field] = format_ms(elapsed_ms)
            write_results(results, fixture_order)
            log(f"Saved {label} for {fixture.name} to {CSV_PATH}")
            fixture_values.append(f"{field.removesuffix('_ms')}={elapsed_ms / 1000:.3f}s" if elapsed_ms is not None else f"{field.removesuffix('_ms')}=FAILED")
        console(f"{fixture.name}: {', '.join(fixture_values)}")

    log(f"Results saved to {CSV_PATH}", console=True)


def generate_plot() -> None:
    if not CSV_PATH.exists():
        log(f"Error: {CSV_PATH} not found. Run with --run first.", console=True)
        return

    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.ticker import FuncFormatter
    except ImportError:
        log("Matplotlib or Numpy not found. Cannot generate plot.", console=True)
        return

    results = []
    known_fixtures = {fixture.name for fixture in FIXTURES}
    with CSV_PATH.open("r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("fixture") not in known_fixtures:
                continue
            if any(is_missing(row.get(field)) for field in CSV_FIELDS if field != "fixture"):
                log(f"Skipping incomplete row in plot: {row.get('fixture', '<unknown>')}")
                continue
            results.append({
                "fixture": row["fixture"],
                "subs2srs_ms": float(row["subs2srs_ms"]),
                "vesta_tsv_ms": float(row["vesta_tsv_ms"]),
                "vesta_apkg_ms": float(row["vesta_apkg_ms"]),
            })

    if not results:
        log(f"No complete benchmark rows found in {CSV_PATH}.", console=True)
        return

    order_index = {fixture: idx for idx, fixture in enumerate(PLOT_ORDER)}
    results.sort(key=lambda row: order_index.get(row["fixture"], len(PLOT_ORDER)))

    labels = [PLOT_LABELS.get(r["fixture"], r["fixture"]) for r in results]
    subs2srs_vals = [r["subs2srs_ms"] for r in results]
    vesta_tsv_vals = [r["vesta_tsv_ms"] for r in results]
    vesta_apkg_vals = [r["vesta_apkg_ms"] for r in results]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(13, len(labels) * 1.35), 8))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#ffffff")

    rects1 = ax.bar(x - width, subs2srs_vals, width, label="subs2srs headless adapter", color="#d95f02")
    rects2 = ax.bar(x, vesta_tsv_vals, width, label="Vesta core - TSV export", color="#1b9e77")
    rects3 = ax.bar(x + width, vesta_apkg_vals, width, label="Vesta core - APKG export", color="#7570b3")

    all_values = subs2srs_vals + vesta_tsv_vals + vesta_apkg_vals
    min_value = min(all_values)
    max_value = max(all_values)

    ax.set_yscale("log")
    ax.set_ylim(max(min_value * 0.65, 1), max_value * 1.85)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}s"))
    ax.set_ylabel("Elapsed time (log scale)")
    ax.set_title("Vesta vs subs2srs benchmark", fontsize=17, fontweight="bold", pad=24)
    ax.text(
        0,
        1.02,
        "Benchmarks use only complete films found directly in Test_Subs; subfolders such as SERIE_TV are ignored.",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        color="#475569",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.legend(loc="upper left", frameon=False, ncols=3)

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(
                f"{height / 1000:.1f}s",
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#334155",
            )

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    ax.grid(axis="y", which="major", linestyle="--", alpha=0.35)
    ax.grid(axis="y", which="minor", linestyle=":", alpha=0.16)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()

    plot_path = ROOT / "benchmark_comparison.png"
    plt.savefig(plot_path, dpi=150)
    log(f"Plot saved to {plot_path}", console=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Vesta core vs subs2srs headless adapter")
    parser.add_argument("--run", action="store_true", help="Execute the benchmarks and save to CSV")
    parser.add_argument("--plot", action="store_true", help="Generate plot from existing CSV")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore existing CSV results, rerun every selected benchmark, and overwrite the CSV",
    )
    parser.add_argument(
        "--fixtures",
        nargs="+",
        help="Optional fixture names to run, e.g. detour interstellar trainspotting zootopia",
    )

    args = parser.parse_args()

    if not args.run and not args.plot:
        args.run = True
        args.plot = True

    selected = set(args.fixtures) if args.fixtures else None

    if args.run:
        perform_benchmarks(selected, reset=args.reset)

    if args.plot:
        generate_plot()


if __name__ == "__main__":
    main()
