"""Command line entry point:  python run_pipeline.py --data-dir data --out-dir results"""
import argparse

from rr_pressure.pipeline import run_all

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run the pressure-rating pipeline.")
    ap.add_argument("--data-dir", default="data", help="folder with the competition CSV files")
    ap.add_argument("--out-dir", default="results", help="folder for the output CSVs and plots")
    args = ap.parse_args()
    run_all(args.data_dir, args.out_dir)
