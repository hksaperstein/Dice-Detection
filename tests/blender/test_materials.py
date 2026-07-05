import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from _harness import run_and_report


def test_all_material_categories_build_without_error():
    import bpy
    from dice_gen import materials

    params = {
        "hue": 0.5, "saturation": 0.7, "value": 0.6, "roughness": 0.3,
        "ior": 1.45, "transmission": 0.9, "noise_scale": 5.0,
        "secondary_hue": 0.1, "sparkle_density": 40.0, "speckle_density": 60.0,
    }
    for category in materials.MATERIAL_CATEGORIES:
        mat = materials.build_material("test_die", category, params)
        assert mat is not None
        assert mat.use_nodes
        assert mat.node_tree.nodes.get("Principled BSDF") is not None


def test_apply_material_appends_to_first_empty_slot():
    import bpy
    from dice_gen import geometry, materials

    obj = geometry.build_die_base_mesh("d6", size_mm=16.0)
    mat = materials.build_material("d6", "opaque", {"hue": 0.2, "saturation": 0.8, "value": 0.5, "roughness": 0.4})
    materials.apply_material(obj, mat, slot_index=0)
    assert len(obj.data.materials) == 1
    assert obj.data.materials[0] is mat
    bpy.data.objects.remove(obj, do_unlink=True)


def test_metallic_material_sets_metallic_input_to_one():
    from dice_gen import materials

    mat = materials.build_material("d20", "metallic", {"hue": 0.6, "saturation": 0.1, "value": 0.8, "roughness": 0.2})
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    assert bsdf.inputs["Metallic"].default_value == 1.0


def run():
    test_all_material_categories_build_without_error()
    test_apply_material_appends_to_first_empty_slot()
    test_metallic_material_sets_metallic_input_to_one()


run_and_report(run)
