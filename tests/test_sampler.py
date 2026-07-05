import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dice_gen import sampler


def test_sample_variant_is_reproducible_with_same_seed():
    a = sampler.sample_variant(42)
    b = sampler.sample_variant(42)
    assert a == b


def test_sample_variant_covers_more_than_one_die_type_across_seeds():
    die_types = {sampler.sample_variant(s).die_type for s in range(50)}
    assert len(die_types) > 1


def test_size_within_configured_range_for_die_type():
    for seed in range(50):
        v = sampler.sample_variant(seed)
        lo, hi = sampler.SIZE_RANGES_MM[v.die_type]
        assert lo <= v.size_mm <= hi


def test_d6_glyph_style_is_numerals_or_pips_only():
    for seed in range(200):
        v = sampler.sample_variant(seed)
        if v.die_type == "d6":
            assert v.glyph_style in ("arabic_numerals", "pips")


def test_non_d6_non_d4_dice_never_use_pips():
    for seed in range(200):
        v = sampler.sample_variant(seed)
        if v.die_type not in ("d6", "d4"):
            assert v.glyph_style != "pips"


def test_glyph_fill_blank_only_possible_for_engraved_method():
    for seed in range(200):
        v = sampler.sample_variant(seed)
        if v.glyph_fill == "blank":
            assert v.glyph_method == "engraved"


def test_d4_placement_set_only_for_d4():
    for seed in range(200):
        v = sampler.sample_variant(seed)
        if v.die_type == "d4":
            assert v.d4_placement in ("face_centered", "vertex_labeled")
        else:
            assert v.d4_placement is None
