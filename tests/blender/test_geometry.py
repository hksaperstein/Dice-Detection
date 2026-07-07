import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from _harness import run_and_report


def test_all_six_dice_build_with_correct_topology():
    import bpy
    from dice_gen import geometry

    for die_type, spec in geometry.DIE_SPECS.items():
        obj = geometry.build_die_base_mesh(die_type, size_mm=16.0)
        n_faces = len(obj.data.polygons)
        n_verts = len(obj.data.vertices)
        n_edges = len(obj.data.edges)

        assert n_faces == spec["expected_faces"], (
            f"{die_type}: expected {spec['expected_faces']} faces, got {n_faces}"
        )
        assert n_verts == spec["expected_verts"], (
            f"{die_type}: expected {spec['expected_verts']} verts, got {n_verts}"
        )
        assert n_edges == spec["expected_edges"], (
            f"{die_type}: expected {spec['expected_edges']} edges, got {n_edges}"
        )
        bpy.data.objects.remove(obj, do_unlink=True)


def test_opposite_face_pairs_are_geometrically_antiparallel_for_d6():
    import bpy
    from dice_gen import geometry

    obj = geometry.build_die_base_mesh("d6", size_mm=16.0)
    pairs = geometry.compute_opposite_face_pairs(obj)
    assert len(pairs) == 3

    obj.data.polygons.foreach_set  # ensure normals accessible
    for a, b in pairs:
        na = obj.data.polygons[a].normal
        nb = obj.data.polygons[b].normal
        dot = na.dot(nb)
        assert dot < -0.99, f"faces {a},{b} not antiparallel (dot={dot})"

    bpy.data.objects.remove(obj, do_unlink=True)


def test_d4_opposite_face_pairs_returns_two_pairs_covering_all_faces():
    import bpy
    from dice_gen import geometry

    obj = geometry.build_die_base_mesh("d4", size_mm=16.0)
    pairs = geometry.compute_opposite_face_pairs(obj)
    flat = sorted(f for pair in pairs for f in pair)
    assert flat == [0, 1, 2, 3]
    bpy.data.objects.remove(obj, do_unlink=True)


def test_build_die_base_mesh_marks_all_edges_with_full_bevel_weight():
    """
    exporter.export_asset's Bevel modifier (see test_exporter.py) selects
    edges to round via limit_method='WEIGHT', not 'ANGLE' -- ANGLE cannot
    tell a die's large structural edges apart from the many small,
    similarly-steep-angled edges bounding an engraved numeral's recess,
    which caused catastrophic degenerate geometry (confirmed on a real
    batch: 42/49 engraved assets affected). This only works if every edge
    of the pristine (pre-engrave) polyhedron is marked with full bevel
    weight before any cut ever runs, since boolean DIFFERENCE cuts don't
    rebuild -- and so don't re-mark -- edges away from the cut region.
    """
    import bmesh
    import bpy
    from dice_gen import geometry

    for die_type, spec in geometry.DIE_SPECS.items():
        obj = geometry.build_die_base_mesh(die_type, size_mm=16.0)

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        layer = bm.edges.layers.float.get('bevel_weight_edge')
        assert layer is not None, f"{die_type}: missing bevel_weight_edge layer"
        weights = [e[layer] for e in bm.edges]
        assert weights == [1.0] * len(bm.edges), (
            f"{die_type}: expected every edge weighted 1.0, got {weights}"
        )
        bm.free()

        bpy.data.objects.remove(obj, do_unlink=True)


def run():
    test_all_six_dice_build_with_correct_topology()
    test_opposite_face_pairs_are_geometrically_antiparallel_for_d6()
    test_d4_opposite_face_pairs_returns_two_pairs_covering_all_faces()
    test_build_die_base_mesh_marks_all_edges_with_full_bevel_weight()


run_and_report(run)
