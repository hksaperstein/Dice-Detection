import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from _harness import run_and_report


def test_generate_batch_produces_manifest_and_assets():
    from dice_gen import orchestrator

    with tempfile.TemporaryDirectory() as outdir:
        generated, failed = orchestrator.generate_batch(count=6, seed=1000, outdir=outdir)

        assert generated + failed == 6
        assert generated >= 1, "at least some assets should succeed"

        manifest_path = os.path.join(outdir, "manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert len(manifest) == generated

        for record in manifest:
            usd_path = os.path.join(outdir, record["usd_path"])
            thumb_path = os.path.join(outdir, record["thumbnail_path"])
            assert os.path.exists(usd_path)
            assert os.path.exists(thumb_path)
            assert record["die_type"] in ("d4", "d6", "d8", "d10", "d12", "d20")

        failures_path = os.path.join(outdir, "failures.json")
        assert os.path.exists(failures_path)


run_and_report(test_generate_batch_produces_manifest_and_assets)
