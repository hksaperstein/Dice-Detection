"""
Parametric construction of the 6 standard TTRPG die shapes.

Each shape is built from a literal list of base vertices (well-known
coordinates for the Platonic solids, plus an empirically-derived pentagonal
trapezohedron for d10 — see _d10_base_vertices) via bmesh's convex_hull +
dissolve_limit. This avoids hand-deriving face/vertex-index topology by
hand: convex_hull computes the correct facets from the point set, and
dissolve_limit merges coplanar hull triangles back into the real N-gon
faces (quads for d10's kites, pentagons for d12, etc).

The d10 vertex ratio (apex height / ring z-offset ≈ 9.47, at ring radius 1)
was found by a numeric sweep confirming near-exact coplanarity (dihedral
deficit < 0.001 deg) of adjacent hull triangles — verified empirically
against this project's installed Blender 5.1.2 before being hardcoded here.
"""
import math

import bmesh
import bpy

PHI = (1 + 5 ** 0.5) / 2
DISSOLVE_ANGLE_DEG = 2.0


class GeometryBuildError(Exception):
    pass


def _d10_base_vertices():
    h, c, r = 0.947, 0.100, 1.0
    verts = [(0, 0, h), (0, 0, -h)]
    for k in range(10):
        theta = math.radians(36 * k)
        z = c if k % 2 == 0 else -c
        verts.append((r * math.cos(theta), r * math.sin(theta), z))
    return verts


DIE_SPECS = {
    "d4": {
        "num_sides": 4,
        "base_vertices": [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)],
        "expected_faces": 4,
        "expected_verts": 4,
        "expected_edges": 6,
    },
    "d6": {
        "num_sides": 6,
        "base_vertices": [(x, y, z) for x in (1, -1) for y in (1, -1) for z in (1, -1)],
        "expected_faces": 6,
        "expected_verts": 8,
        "expected_edges": 12,
    },
    "d8": {
        "num_sides": 8,
        "base_vertices": [
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1),
        ],
        "expected_faces": 8,
        "expected_verts": 6,
        "expected_edges": 12,
    },
    "d10": {
        "num_sides": 10,
        "base_vertices": _d10_base_vertices(),
        "expected_faces": 10,
        "expected_verts": 12,
        "expected_edges": 20,
    },
    "d12": {
        "num_sides": 12,
        "base_vertices": (
            [(x, y, z) for x in (1, -1) for y in (1, -1) for z in (1, -1)]
            + [(0, s1 / PHI, s2 * PHI) for s1 in (1, -1) for s2 in (1, -1)]
            + [(s1 / PHI, s2 * PHI, 0) for s1 in (1, -1) for s2 in (1, -1)]
            + [(s1 * PHI, 0, s2 / PHI) for s1 in (1, -1) for s2 in (1, -1)]
        ),
        "expected_faces": 12,
        "expected_verts": 20,
        "expected_edges": 30,
    },
    "d20": {
        "num_sides": 20,
        "base_vertices": (
            [(0, s1 * 1, s2 * PHI) for s1 in (1, -1) for s2 in (1, -1)]
            + [(s1 * 1, s2 * PHI, 0) for s1 in (1, -1) for s2 in (1, -1)]
            + [(s1 * PHI, 0, s2 * 1) for s1 in (1, -1) for s2 in (1, -1)]
        ),
        "expected_faces": 20,
        "expected_verts": 12,
        "expected_edges": 30,
    },
}


def build_die_base_mesh(die_type, size_mm):
    spec = DIE_SPECS[die_type]
    scale = size_mm / 2.0

    bm = bmesh.new()
    bmverts = [bm.verts.new((x * scale, y * scale, z * scale)) for (x, y, z) in spec["base_vertices"]]
    bmesh.ops.convex_hull(bm, input=bmverts)
    bmesh.ops.dissolve_limit(
        bm, angle_limit=math.radians(DISSOLVE_ANGLE_DEG), verts=bm.verts, edges=bm.edges
    )
    bm.faces.ensure_lookup_table()
    bm.normal_update()

    if len(bm.faces) != spec["expected_faces"] or len(bm.verts) != spec["expected_verts"]:
        n_faces, n_verts = len(bm.faces), len(bm.verts)
        bm.free()
        raise GeometryBuildError(
            f"{die_type}: expected {spec['expected_faces']} faces / {spec['expected_verts']} verts, "
            f"got {n_faces} faces / {n_verts} verts"
        )

    # Mark every structural edge of the pristine polyhedron before any
    # engraving cut ever runs -- see exporter.export_asset's Bevel modifier
    # (limit_method='WEIGHT') for why this must happen here rather than
    # right before bevel: boolean DIFFERENCE cuts don't rebuild untouched
    # edges away from the cut, so this weight survives every cut intact,
    # letting the eventual bevel round only the die's real structural
    # edges and never the many similarly-steep-angled edges an engraved
    # numeral's recess introduces.
    bevel_layer = bm.edges.layers.float.new('bevel_weight_edge')
    for e in bm.edges:
        e[bevel_layer] = 1.0

    mesh = bpy.data.meshes.new(f"{die_type}_mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(f"{die_type}_die", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def compute_opposite_face_pairs(obj):
    """
    Returns [(face_index_a, face_index_b), ...] pairs. For the 5 centrally
    symmetric dice (d6/d8/d10/d12/d20) these are true antipodal face pairs
    (most anti-parallel normals, greedily matched). d4 (tetrahedron) has no
    antipodal faces — its numbering has no opposite_sum rule anyway, so this
    just returns a stable consecutive grouping.
    """
    faces = list(obj.data.polygons)
    n = len(faces)
    if n == 4:
        return [(0, 1), (2, 3)]

    remaining = set(range(n))
    pairs = []
    while remaining:
        i = min(remaining)
        remaining.discard(i)
        best_j, best_dot = None, 2.0
        for j in remaining:
            dot = faces[i].normal.dot(faces[j].normal)
            if dot < best_dot:
                best_dot = dot
                best_j = j
        pairs.append((i, best_j))
        remaining.discard(best_j)
    return pairs
