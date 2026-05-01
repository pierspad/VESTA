import os
import subprocess
import time
import csv
import shutil
import argparse

# Configuration
VESTA_BIN = "target/release/vesta"
SUBS2SRS_BIN = "dotnet subs2srs_source/subs2srs/bin/Release/net10.0/subs2srs.dll --cli"
OUTPUT_DIR = "/tmp/benchmarks_out"
CSV_PATH = "benchmarks_result.csv"

FIXTURES_DIR = "Test_Subs/fixtures"
FIXTURES = [
    "clip_01",
    "clip_02",
    "clip_03",
    "clip_04",
    "clip_05"
]

def run_subs2srs(base_name):
    print(f"Running subs2srs for {base_name}...")
    sub1 = os.path.join(FIXTURES_DIR, f"{base_name}_en.srt")
    sub2 = os.path.join(FIXTURES_DIR, f"{base_name}_it.srt")
    video = os.path.join(FIXTURES_DIR, f"{base_name}.mp4")
    
    out_dir = os.path.join(OUTPUT_DIR, f"subs2srs_{base_name}")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    
    cmd = f"{SUBS2SRS_BIN} {sub1} {sub2} {video} {out_dir}"
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end_time = time.time()
    
    if result.returncode != 0:
        print(f"subs2srs failed for {base_name}: {result.stderr}")
        return None
    
    return (end_time - start_time) * 1000  # ms

def run_vesta(base_name, export_fmt):
    print(f"Running Vesta ({export_fmt}) for {base_name}...")
    sub1 = os.path.join(FIXTURES_DIR, f"{base_name}_en.srt")
    sub2 = os.path.join(FIXTURES_DIR, f"{base_name}_it.srt")
    video = os.path.join(FIXTURES_DIR, f"{base_name}.mp4")
    
    out_dir = os.path.join(OUTPUT_DIR, f"vesta_{export_fmt}_{base_name}")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    
    cmd = f"{VESTA_BIN} --benchmark {sub1} {sub2} {video} {out_dir} {export_fmt}"
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Vesta failed for {base_name}: {result.stderr}")
        return None
        
    for line in result.stdout.split('\n'):
        if line.startswith("VESTA_BENCHMARK_SUCCESS:"):
            try:
                ms = int(line.split(":")[1].replace("ms", "").strip())
                return ms
            except ValueError:
                pass
    
    print(f"Could not parse Vesta output for {base_name}")
    return None

def perform_benchmarks():
    if not os.path.exists(VESTA_BIN):
        print(f"Compiling Vesta in release mode...")
        subprocess.run("cd apps/srt-gui/src-tauri && cargo build --release", shell=True, check=True)
        
    results = []
    
    for fixture in FIXTURES:
        subs2srs_time = run_subs2srs(fixture)
        vesta_tsv_time = run_vesta(fixture, "tsv")
        vesta_apkg_time = run_vesta(fixture, "apkg")
        
        results.append({
            "fixture": fixture,
            "subs2srs_ms": subs2srs_time or 0,
            "vesta_tsv_ms": vesta_tsv_time or 0,
            "vesta_apkg_ms": vesta_apkg_time or 0
        })
        
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["fixture", "subs2srs_ms", "vesta_tsv_ms", "vesta_apkg_ms"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)
            
    print(f"Results saved to {CSV_PATH}")

def generate_plot():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found. Run with --run first.")
        return

    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        results = []
        with open(CSV_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append({
                    "fixture": row["fixture"],
                    "subs2srs_ms": float(row["subs2srs_ms"]),
                    "vesta_tsv_ms": float(row["vesta_tsv_ms"]),
                    "vesta_apkg_ms": float(row["vesta_apkg_ms"])
                })

        labels = [r["fixture"] for r in results]
        subs2srs_vals = [r["subs2srs_ms"] for r in results]
        vesta_tsv_vals = [r["vesta_tsv_ms"] for r in results]
        vesta_apkg_vals = [r["vesta_apkg_ms"] for r in results]
        
        x = np.arange(len(labels))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(12, 7))
        rects1 = ax.bar(x - width, subs2srs_vals, width, label='subs2srs (TSV)', color='#e74c3c')
        rects2 = ax.bar(x, vesta_tsv_vals, width, label='Vesta (TSV)', color='#3498db')
        rects3 = ax.bar(x + width, vesta_apkg_vals, width, label='Vesta (APKG)', color='#2ecc71')
        
        ax.set_ylabel('Time (ms)')
        ax.set_title('Performance Comparison: subs2srs vs Vesta', fontsize=16)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()
        
        # Add labels on top of bars
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.0f}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

        autolabel(rects1)
        autolabel(rects2)
        autolabel(rects3)
        
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        fig.tight_layout()
        
        plot_path = "benchmark_comparison.png"
        plt.savefig(plot_path, dpi=150)
        print(f"Plot saved to {plot_path}")
        
    except ImportError:
        print("Matplotlib or Numpy not found. Cannot generate plot.")

def main():
    parser = argparse.ArgumentParser(description="Benchmark Vesta vs subs2srs")
    parser.add_argument("--run", action="store_true", help="Execute the benchmarks and save to CSV")
    parser.add_argument("--plot", action="store_true", help="Generate plot from existing CSV")
    
    args = parser.parse_args()
    
    # If no flags provided, do both
    if not args.run and not args.plot:
        args.run = True
        args.plot = True
        
    if args.run:
        perform_benchmarks()
        
    if args.plot:
        generate_plot()

if __name__ == "__main__":
    main()
