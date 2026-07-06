"""
Bakes the non-destructive edge fillet, saves the finished model as a
standalone .blend FIRST (before any export), then exports the die as
USD/STL, renders a thumbnail for visual spot-checking, and writes the
per-asset JSON manifest.

The .blend save happens before USD/STL/thumbnail so it always captures the
fully-finished model as the definitive source state everything else is
derived from -- and, as a side effect, so the thumbnail render's own
temporary camera/light objects never exist yet at .blend-save time (they're
created and removed afterward), which would otherwise leak into the saved
.blend the same way Blender's default startup Cube/Light/Camera would (see
_save_blend_copy).

The Bevel modifier's segments=8 (rather than the default 1) produces a
smooth rounded fillet on the die's structural edges/corners instead of a
single flat chamfer facet. limit_method='ANGLE' (not 'NONE') ensures it
only rounds those structural edges (e.g. a cube's ~90 degree edges) while
leaving shallow engraved-numeral recesses (much shallower angle deltas)
crisp.
"""
import json
import math
import os

import bpy


def export_asset(die_obj, manifest_record, outdir, bevel_fraction, size_mm):
    os.makedirs(outdir, exist_ok=True)
    asset_id = manifest_record["asset_id"]

    mod = die_obj.modifiers.new(name="Bevel", type='BEVEL')
    mod.width = size_mm * bevel_fraction
    mod.segments = 8
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(35)
    bpy.context.view_layer.objects.active = die_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.ops.object.select_all(action='DESELECT')
    die_obj.select_set(True)
    bpy.context.view_layer.objects.active = die_obj

    blend_path = os.path.join(outdir, f"{asset_id}.blend")
    _save_blend_copy(blend_path)

    usd_path = os.path.join(outdir, f"{asset_id}.usd")
    bpy.ops.wm.usd_export(filepath=usd_path, selected_objects_only=True)

    stl_path = os.path.join(outdir, f"{asset_id}.stl")
    bpy.ops.wm.stl_export(filepath=stl_path, export_selected_objects=True)

    thumb_path = os.path.join(outdir, f"{asset_id}_thumb.png")
    _render_thumbnail(die_obj, thumb_path, size_mm)

    manifest_record["usd_path"] = f"{asset_id}.usd"
    manifest_record["stl_path"] = f"{asset_id}.stl"
    manifest_record["blend_path"] = f"{asset_id}.blend"
    manifest_record["thumbnail_path"] = f"{asset_id}_thumb.png"
    manifest_path = os.path.join(outdir, f"{asset_id}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_record, f, indent=2)

    return manifest_path


def _save_blend_copy(blend_path):
    """
    Saves the current .blend state as a standalone copy the user can open
    directly in Blender, with color/texture/material immediately visible.
    Three things have to be handled explicitly here that usd_export/
    stl_export don't need to worry about, since save_as_mainfile has no
    "selected objects only" option -- it always saves Blender's entire
    current file:

    1. Blender's own default-startup scene (present in every
       `blender --background --python ...` session that doesn't load an
       explicit .blend file) links a "Cube", "Light", and "Camera" object
       into the scene. Nothing in this pipeline uses them, but they'd
       otherwise silently end up saved into every single asset's .blend
       alongside the actual die.
    2. This function runs once per asset inside one long-running batch
       session (see orchestrator.generate_batch/generate_set_batch). Each
       previous asset's die object is removed via
       bpy.data.objects.remove(..., do_unlink=True) at the end of its own
       iteration, which unlinks it from the scene but leaves its
       mesh/material/image data-blocks resident in bpy.data with zero
       users. Without purging these first, every later asset's saved
       .blend would accumulate every earlier asset's orphaned data too
       (confirmed empirically: mesh/material counts and file size grew on
       every iteration of a save loop without this purge, and stayed flat
       once it was added).
    3. Blender's default viewport shading mode ("Solid") doesn't evaluate
       the shader node graph at all -- it shows a material's separate
       diffuse_color property instead (see materials.py). Setting every
       VIEW_3D viewport's shading to Material Preview means opening this
       .blend shows the die's real color/texture/material immediately, on
       whichever workspace tab (Layout, Modeling, Shading, etc.) happens
       to be active, with no manual shading-mode switch needed. Confirmed
       feasible even in --background mode: every one of Blender's default
       workspace screens has a real, settable VIEW_3D area.

    copy=True is required so saving this per-asset .blend never changes
    the long-running batch session's own "current file" identity.
    """
    for name in ("Cube", "Light", "Camera"):
        stray = bpy.data.objects.get(name)
        if stray is not None:
            bpy.data.objects.remove(stray, do_unlink=True)

    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True, check_existing=False)


def _render_thumbnail(die_obj, thumb_path, size_mm, resolution=512):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.film_transparent = True

    cam_data = bpy.data.cameras.new(f"{die_obj.name}_cam")
    # Widen the field of view (default lens is 50mm) so the die comfortably
    # fits the frame even at the generous distance below.
    cam_data.lens = 35
    cam_obj = bpy.data.objects.new(f"{die_obj.name}_cam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    # The die's own vertices extend up to roughly size_mm in radius from the
    # origin (e.g. a d20's base vertices reach ~0.95 * size_mm). Placing the
    # camera at (dist, -dist, dist) puts it sqrt(3) * dist from the origin,
    # so dist must be well above size_mm to sit clearly outside the die's
    # geometry with headroom to frame the whole object.
    dist = size_mm * 2.2
    cam_obj.location = (dist, -dist, dist)
    direction = die_obj.location - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam_obj

    light_data = bpy.data.lights.new(f"{die_obj.name}_light", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(f"{die_obj.name}_light", light_data)
    light_obj.location = (dist, dist, dist * 1.5)
    bpy.context.collection.objects.link(light_obj)

    scene.render.filepath = thumb_path
    bpy.ops.render.render(write_still=True)

    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.objects.remove(light_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    bpy.data.lights.remove(light_data)
