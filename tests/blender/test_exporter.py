import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from _harness import run_and_report


def test_export_asset_writes_usd_manifest_and_thumbnail():
    import bpy
    from dice_gen import geometry, materials, exporter

    obj = geometry.build_die_base_mesh("d6", size_mm=16.0)
    mat = materials.build_material("d6", "opaque", {"hue": 0.3, "saturation": 0.7, "value": 0.6, "roughness": 0.4})
    materials.apply_material(obj, mat)

    with tempfile.TemporaryDirectory() as outdir:
        record = {"asset_id": "test_d6", "die_type": "d6"}
        manifest_path = exporter.export_asset(obj, record, outdir, bevel_fraction=0.04, size_mm=16.0)

        usd_path = os.path.join(outdir, "test_d6.usd")
        thumb_path = os.path.join(outdir, "test_d6_thumb.png")
        stl_path = os.path.join(outdir, "test_d6.stl")
        blend_path = os.path.join(outdir, "test_d6.blend")

        assert os.path.exists(usd_path) and os.path.getsize(usd_path) > 0
        assert os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0
        assert os.path.exists(stl_path) and os.path.getsize(stl_path) > 0
        assert os.path.exists(blend_path) and os.path.getsize(blend_path) > 0
        assert os.path.exists(manifest_path)

        with open(manifest_path) as f:
            loaded = json.load(f)
        assert loaded["usd_path"] == "test_d6.usd"
        assert loaded["thumbnail_path"] == "test_d6_thumb.png"
        assert loaded["stl_path"] == "test_d6.stl"
        assert loaded["blend_path"] == "test_d6.blend"

    bpy.data.objects.remove(obj, do_unlink=True)


def test_export_asset_blend_file_contains_only_the_die_object():
    """
    export_asset's saved .blend must contain exactly the die object, not
    Blender's own default-startup "Cube"/"Light"/"Camera" objects that a
    `blender --background --python ...` session links into the scene by
    default whenever no explicit .blend is loaded (confirmed empirically
    during planning: a fresh headless session's scene contains exactly
    those three objects). Unlike usd_export/stl_export (both take a
    selected-objects-only flag), save_as_mainfile has no such option and
    always saves the entire current file, so this guarantee has to be
    established explicitly in export_asset itself.
    """
    import bpy
    from dice_gen import geometry, materials, exporter

    obj = geometry.build_die_base_mesh("d6", size_mm=16.0)
    mat = materials.build_material("d6", "opaque", {"hue": 0.3, "saturation": 0.7, "value": 0.6, "roughness": 0.4})
    materials.apply_material(obj, mat)
    obj_name = obj.name

    with tempfile.TemporaryDirectory() as outdir:
        record = {"asset_id": "test_single", "die_type": "d6"}
        exporter.export_asset(obj, record, outdir, bevel_fraction=0.04, size_mm=16.0)

        blend_path = os.path.join(outdir, "test_single.blend")
        with bpy.data.libraries.load(blend_path) as (data_from, _data_to):
            objects_in_file = list(data_from.objects)

        assert objects_in_file == [obj_name], (
            f"expected the saved .blend to contain only the die object "
            f"{obj_name!r} and nothing else (no default Cube/Light/Camera), "
            f"got {objects_in_file}"
        )

    bpy.data.objects.remove(obj, do_unlink=True)


def test_export_asset_blend_files_do_not_accumulate_across_multiple_exports():
    """
    Regression test for orphaned-data-block accumulation across a batch:
    in one long-running `blender --background` session, each previous
    asset's die object is removed via bpy.data.objects.remove(...,
    do_unlink=True) (see orchestrator._generate_from_params) which unlinks
    it from the scene but leaves its mesh/material data resident in
    bpy.data with zero users. Confirmed empirically during planning that
    without purging these before each save_as_mainfile call, every later
    asset's .blend silently accumulates every earlier asset's orphaned
    mesh/material data too (mesh/material counts and file size grew on
    every iteration of a throwaway repro loop; purging before each save
    kept both flat). This test exports two different dice in the same
    session and asserts each one's saved .blend contains only its own
    object/mesh/material data, not the other's.
    """
    import bpy
    from dice_gen import geometry, materials, exporter

    obj1 = geometry.build_die_base_mesh("d6", size_mm=16.0)
    mat1 = materials.build_material("d6", "opaque", {"hue": 0.3, "saturation": 0.7, "value": 0.6, "roughness": 0.4})
    materials.apply_material(obj1, mat1)
    obj1_name = obj1.name
    mesh1_name = obj1.data.name
    mat1_name = mat1.name

    with tempfile.TemporaryDirectory() as outdir:
        record1 = {"asset_id": "test_first", "die_type": "d6"}
        exporter.export_asset(obj1, record1, outdir, bevel_fraction=0.04, size_mm=16.0)
        bpy.data.objects.remove(obj1, do_unlink=True)

        obj2 = geometry.build_die_base_mesh("d4", size_mm=14.0)
        mat2 = materials.build_material("d4", "opaque", {"hue": 0.6, "saturation": 0.5, "value": 0.5, "roughness": 0.3})
        materials.apply_material(obj2, mat2)
        obj2_name = obj2.name
        mesh2_name = obj2.data.name
        mat2_name = mat2.name

        record2 = {"asset_id": "test_second", "die_type": "d4"}
        exporter.export_asset(obj2, record2, outdir, bevel_fraction=0.04, size_mm=14.0)

        blend1_path = os.path.join(outdir, "test_first.blend")
        blend2_path = os.path.join(outdir, "test_second.blend")

        with bpy.data.libraries.load(blend1_path) as (data_from, _data_to):
            objects_in_first = list(data_from.objects)
            meshes_in_first = list(data_from.meshes)
            materials_in_first = list(data_from.materials)
        with bpy.data.libraries.load(blend2_path) as (data_from, _data_to):
            objects_in_second = list(data_from.objects)
            meshes_in_second = list(data_from.meshes)
            materials_in_second = list(data_from.materials)

        assert objects_in_first == [obj1_name], (
            f"the first asset's .blend should contain only its own die "
            f"({obj1_name!r}); obj1 was already removed from the live "
            f"scene before this check, so this reads back what was "
            f"actually written to disk, got {objects_in_first}"
        )
        assert objects_in_second == [obj2_name], (
            f"the second asset's .blend should contain only its own die "
            f"({obj2_name!r}), not any orphaned data left over from the "
            f"first asset, got {objects_in_second}"
        )

        # Mesh data for the first asset
        assert meshes_in_first == [mesh1_name], (
            f"the first asset's .blend should contain only its own mesh data "
            f"({mesh1_name!r}), got {meshes_in_first}"
        )
        # Material data for the first asset
        assert materials_in_first == [mat1_name], (
            f"the first asset's .blend should contain only its own material "
            f"({mat1_name!r}), got {materials_in_first}"
        )

        # Mesh data for the second asset must not include the first die's mesh
        assert mesh1_name not in meshes_in_second, (
            f"the second asset's .blend should NOT contain the first asset's mesh "
            f"({mesh1_name!r}), which would indicate orphaned data accumulation; "
            f"got meshes: {meshes_in_second}"
        )
        assert meshes_in_second == [mesh2_name], (
            f"the second asset's .blend should contain only its own mesh data "
            f"({mesh2_name!r}), got {meshes_in_second}"
        )

        # Material data for the second asset must not include the first die's material
        assert mat1_name not in materials_in_second, (
            f"the second asset's .blend should NOT contain the first asset's material "
            f"({mat1_name!r}), which would indicate orphaned data accumulation; "
            f"got materials: {materials_in_second}"
        )
        assert materials_in_second == [mat2_name], (
            f"the second asset's .blend should contain only its own material "
            f"({mat2_name!r}), got {materials_in_second}"
        )

        bpy.data.objects.remove(obj2, do_unlink=True)


def run():
    test_export_asset_writes_usd_manifest_and_thumbnail()
    test_export_asset_blend_file_contains_only_the_die_object()
    test_export_asset_blend_files_do_not_accumulate_across_multiple_exports()


run_and_report(run)
