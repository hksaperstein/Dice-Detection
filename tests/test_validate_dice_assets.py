import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validate_dice_assets import validate


def _write_manifest(tmp_path, records):
    with open(os.path.join(tmp_path, "manifest.json"), "w") as f:
        json.dump(records, f)


def test_validate_reports_missing_usd_file(tmp_path):
    _write_manifest(tmp_path, [{
        "asset_id": "a1", "die_type": "d6", "num_sides": 6,
        "usd_path": "a1.usd", "thumbnail_path": "a1_thumb.png",
    }])
    open(os.path.join(tmp_path, "a1_thumb.png"), "w").close()

    errors = validate(str(tmp_path))
    assert any("missing USD" in e for e in errors)


def test_validate_reports_wrong_num_sides():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_path:
        _write_manifest(tmp_path, [{
            "asset_id": "a1", "die_type": "d6", "num_sides": 5,
            "usd_path": "a1.usd", "thumbnail_path": "a1_thumb.png",
        }])
        open(os.path.join(tmp_path, "a1.usd"), "w").write("x")
        open(os.path.join(tmp_path, "a1_thumb.png"), "w").close()

        errors = validate(tmp_path)
        assert any("num_sides" in e for e in errors)


def test_validate_passes_for_well_formed_manifest():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_path:
        _write_manifest(tmp_path, [{
            "asset_id": "a1", "die_type": "d20", "num_sides": 20,
            "usd_path": "a1.usd", "thumbnail_path": "a1_thumb.png",
        }])
        open(os.path.join(tmp_path, "a1.usd"), "w").write("x")
        open(os.path.join(tmp_path, "a1_thumb.png"), "w").close()

        errors = validate(tmp_path)
        assert errors == []
