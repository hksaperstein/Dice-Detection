import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dice_gen import orchestrator


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    parser = argparse.ArgumentParser(description="Generate a library of dice USD assets.")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", type=str, default="data/raw/dice_assets")
    args = parser.parse_args(argv)

    generated, failed = orchestrator.generate_batch(args.count, args.seed, args.outdir)
    print(f"Generated: {generated}, Failed: {failed}")


if __name__ == "__main__":
    main()
