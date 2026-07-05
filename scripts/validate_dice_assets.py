import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dice_gen import numbering


def validate(outdir):
    manifest_path = os.path.join(outdir, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    errors = []
    for record in manifest:
        asset_id = record["asset_id"]
        usd_path = os.path.join(outdir, record["usd_path"])
        thumb_path = os.path.join(outdir, record["thumbnail_path"])

        if not os.path.exists(usd_path):
            errors.append(f"{asset_id}: missing USD file {usd_path}")
        elif os.path.getsize(usd_path) == 0:
            errors.append(f"{asset_id}: empty USD file {usd_path}")

        if not os.path.exists(thumb_path):
            errors.append(f"{asset_id}: missing thumbnail {thumb_path}")

        die_type = record["die_type"]
        expected_sides = len(numbering.get_values(die_type))
        if record["num_sides"] != expected_sides:
            errors.append(
                f"{asset_id}: num_sides {record['num_sides']} != expected "
                f"{expected_sides} for {die_type}"
            )

    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir")
    args = parser.parse_args()

    found_errors = validate(args.outdir)
    print(f"Checked manifest at {args.outdir}: {len(found_errors)} error(s).")
    for e in found_errors:
        print(" -", e)
    sys.exit(1 if found_errors else 0)
