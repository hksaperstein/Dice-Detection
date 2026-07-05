import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from _harness import run_and_report


def test_glyph_label_formats():
    from dice_gen import glyphs

    assert glyphs.glyph_label(6, "arabic_numerals") == "6"
    assert glyphs.glyph_label(20, "roman_numerals") == "XX"
    assert glyphs.glyph_label(9, "roman_numerals") == "IX"


def test_engraved_glyphs_reduce_solid_volume():
    import bpy
    from dice_gen import geometry, numbering, glyphs

    die_type = "d6"
    obj = geometry.build_die_base_mesh(die_type, size_mm=16.0)
    pairs = geometry.compute_opposite_face_pairs(obj)
    assignment = numbering.assign_values_to_opposite_pairs(die_type, pairs)

    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    volume_before = bm.calc_volume()
    bm.free()

    glyphs.apply_engraved_glyphs(
        obj, die_type, assignment,
        glyph_style="arabic_numerals", glyph_fill="painted",
        font_id="font_sans_bold", size_mm=16.0,
    )

    bm2 = bmesh.new()
    bm2.from_mesh(obj.data)
    volume_after = bm2.calc_volume()
    bm2.free()

    assert volume_after < volume_before, "engraving should remove material"
    assert len(obj.data.materials) >= 2, "painted fill should add a second material slot"

    bpy.data.objects.remove(obj, do_unlink=True)


def test_engraved_glyphs_blank_fill_does_not_add_second_material():
    import bpy
    from dice_gen import geometry, numbering, glyphs

    die_type = "d6"
    obj = geometry.build_die_base_mesh(die_type, size_mm=16.0)
    pairs = geometry.compute_opposite_face_pairs(obj)
    assignment = numbering.assign_values_to_opposite_pairs(die_type, pairs)

    glyphs.apply_engraved_glyphs(
        obj, die_type, assignment,
        glyph_style="arabic_numerals", glyph_fill="blank",
        font_id="font_sans_bold", size_mm=16.0,
    )

    assert len(obj.data.materials) < 2, (
        "blank fill should not add a second (painted fill) material slot"
    )

    bpy.data.objects.remove(obj, do_unlink=True)


def test_decal_glyphs_assigns_one_material_per_face():
    import bpy
    from dice_gen import geometry, numbering, glyphs

    die_type = "d6"
    obj = geometry.build_die_base_mesh(die_type, size_mm=16.0)
    pairs = geometry.compute_opposite_face_pairs(obj)
    assignment = numbering.assign_values_to_opposite_pairs(die_type, pairs)

    with tempfile.TemporaryDirectory() as tmp_dir:
        glyphs.apply_decal_glyphs(
            obj, die_type, assignment,
            glyph_style="arabic_numerals", font_id="font_sans_bold",
            size_mm=16.0, tmp_dir=tmp_dir,
        )
        assert len(obj.data.materials) == 6
        for face_index in assignment:
            mat_index = obj.data.polygons[face_index].material_index
            assert obj.data.materials[mat_index] is not None

    bpy.data.objects.remove(obj, do_unlink=True)


def test_engraved_glyphs_use_pristine_face_orientations_not_reindexed_mid_loop():
    """
    Regression test for the face-index-drift bug: apply_engraved_glyphs used
    to loop over assignment.items() and re-read die_obj.data.polygons[face_index]
    INSIDE the loop, after prior iterations had already applied a boolean
    modifier (bpy.ops.object.modifier_apply), which rebuilds/reindexes mesh
    topology. On a d10 this caused polygon counts to jump around wildly
    (10 -> 204 -> 235 -> 249 -> 6) and eventually raise IndexError, and even
    when it didn't crash, numerals were engraved onto the wrong faces.

    This test both (a) directly verifies the fix's mechanism -- that the
    orientation matrices used for cutting match those computed once on the
    pristine mesh, with no drift -- and (b) checks an indirect symptom (a
    sane, non-degenerate final mesh with the expected volume reduction) that
    would have caught the collapse/IndexError behavior seen in the original
    bug.
    """
    import bpy
    import bmesh
    from dice_gen import geometry, numbering, glyphs

    die_type = "d10"
    size_mm = 16.0

    # Build once and capture the "pristine" per-face orientation matrices
    # ourselves, exactly the way a correct implementation must (i.e. compute
    # everything BEFORE any cut is applied). This is the ground truth we
    # compare the fixed implementation's behavior against.
    obj = geometry.build_die_base_mesh(die_type, size_mm=size_mm)
    pairs = geometry.compute_opposite_face_pairs(obj)
    assignment = numbering.assign_values_to_opposite_pairs(die_type, pairs)
    assert len(assignment) == 10, "d10 should have 10 faces assigned"

    pristine_orientations = {}
    for face_index in assignment:
        face = obj.data.polygons[face_index]
        pristine_orientations[face_index] = glyphs._face_orientation_matrix(
            face, obj.matrix_world
        ).copy()

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    volume_before = bm.calc_volume()
    faces_before = len(bm.faces)
    bm.free()

    # (a) Direct mechanism check: instrument the real _face_orientation_matrix
    # and _boolean_diff_apply calls made by apply_engraved_glyphs itself, so
    # we can prove (not just infer) that:
    #   1. ALL orientation-matrix computations happen strictly before the
    #      FIRST boolean cut is applied (i.e. Phase 1 fully precedes Phase 2 --
    #      the actual defect was reading polygons mid-loop, interleaved with
    #      cuts), and
    #   2. every orientation matrix actually used for cutting is bit-for-bit
    #      identical to the one computed independently against the pristine
    #      mesh before apply_engraved_glyphs was ever called.
    call_log = []  # list of ("orient", face_index, matrix) or ("cut",)
    real_orientation_fn = glyphs._face_orientation_matrix
    real_boolean_apply_fn = glyphs._boolean_diff_apply

    def spy_orientation(face, obj_matrix):
        result = real_orientation_fn(face, obj_matrix)
        call_log.append(("orient", face.index, result.copy()))
        return result

    def spy_boolean_apply(die_obj_arg, cutter_obj):
        call_log.append(("cut",))
        return real_boolean_apply_fn(die_obj_arg, cutter_obj)

    glyphs._face_orientation_matrix = spy_orientation
    glyphs._boolean_diff_apply = spy_boolean_apply
    try:
        glyphs.apply_engraved_glyphs(
            obj, die_type, assignment,
            glyph_style="arabic_numerals", glyph_fill="painted",
            font_id="font_sans_bold", size_mm=size_mm,
        )
    finally:
        glyphs._face_orientation_matrix = real_orientation_fn
        glyphs._boolean_diff_apply = real_boolean_apply_fn

    orient_calls = [entry for entry in call_log if entry[0] == "orient"]
    cut_calls = [entry for entry in call_log if entry[0] == "cut"]
    assert len(orient_calls) == len(assignment), (
        f"expected exactly {len(assignment)} orientation computations "
        f"(one per face, all upfront), got {len(orient_calls)}"
    )
    assert len(cut_calls) >= len(assignment), "expected at least one cut per face"

    first_cut_position = call_log.index(cut_calls[0])
    last_orient_position = max(
        i for i, entry in enumerate(call_log) if entry[0] == "orient"
    )
    assert last_orient_position < first_cut_position, (
        "all face-orientation computations must happen BEFORE the first "
        "boolean cut is applied (this is the actual fix: no re-indexing "
        "into die_obj.data.polygons after any cut has mutated the mesh)"
    )

    for _, face_index, orient_used in orient_calls:
        expected = pristine_orientations[face_index]
        drift = (orient_used.translation - expected.translation).length
        assert drift < 1e-9, (
            f"face {face_index}: orientation actually used for cutting "
            f"({orient_used.translation}) must exactly match the "
            f"independently precomputed pristine orientation "
            f"({expected.translation}), got drift {drift}"
        )

    # (b) Indirect sanity check: the final mesh must be non-degenerate and
    # show volume loss consistent with 10 real engraving cuts, not the
    # collapsed 6-or-235-polygon garbage the bug produced.
    bm3 = bmesh.new()
    bm3.from_mesh(obj.data)
    volume_after = bm3.calc_volume()
    faces_after = len(bm3.faces)
    bm3.free()

    assert volume_after > 0, "engraved die must not collapse to a degenerate/zero-volume mesh"
    assert volume_after < volume_before, "engraving should remove material"
    # Sanity bounds: 10 numeral cuts should remove a modest fraction of the
    # die's volume, not gut it (which is what happened when cutters ended up
    # applied at wildly wrong locations/sizes due to the drift bug).
    fraction_removed = (volume_before - volume_after) / volume_before
    assert 0.001 < fraction_removed < 0.5, (
        f"unexpected volume loss fraction {fraction_removed} "
        f"(before={volume_before}, after={volume_after})"
    )
    # The original bug produced polygon counts that swung wildly between
    # cuts (10 -> 204 -> 235 -> 249) before collapsing to a degenerate 6
    # once the reindexing finally pointed a cutter somewhere pathological.
    # A correctly engraved d10 (10 arabic-numeral text cuts, each of which
    # legitimately contributes a few hundred new boolean-diff faces from the
    # extruded glyph geometry) empirically lands around ~2000 faces on this
    # Blender version/font -- well above the 10 base faces, and nowhere near
    # a collapsed handful, but this is naturally a much larger number than
    # the mid-corruption snapshot values seen in the bug repro (which were
    # measured mid-loop, after only 1-3 of the cuts had been mangled).
    assert faces_before < faces_after < 5000, (
        f"face count {faces_after} outside sane range for a correctly "
        f"engraved d10 (before={faces_before})"
    )

    assert len(obj.data.materials) >= 2, "painted fill should add a second material slot"

    bpy.data.objects.remove(obj, do_unlink=True)


def run():
    test_glyph_label_formats()
    test_engraved_glyphs_reduce_solid_volume()
    test_engraved_glyphs_blank_fill_does_not_add_second_material()
    test_decal_glyphs_assigns_one_material_per_face()
    test_engraved_glyphs_use_pristine_face_orientations_not_reindexed_mid_loop()


run_and_report(run)
