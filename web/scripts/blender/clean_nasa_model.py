"""Prepare an official NASA/JPL 3D model for the viewer (run in background Blender).

  blender -b --factory-startup --python clean_nasa_model.py -- <in.glb> <clean_textures_dir> <out.glb> <decimate_ratio> <max_texture_px> <yaw_deg>

- Replaces the model's textures with versions where agency branding (logos, flag, mission
  plaques, perforated agency names, commemorative and brand text) was painted out with the
  surrounding plain surface (see web/scripts/blender/README.md). Nothing of the marks is kept.
- Optionally decimates heavy meshes and downsizes textures for the web.
- Rotates the model so its front faces +X (east at yaw 0 in the viewer).
Geometry and the remaining textures are NASA/JPL-Caltech's; only this preparation is ours.
"""
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
src, clean_dir, dst = args[0], args[1], args[2]
ratio = float(args[3]) if len(args) > 3 else 1.0
max_px = int(args[4]) if len(args) > 4 else 1024
yaw = float(args[5]) if len(args) > 5 else 0.0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

replaced = []
for img in bpy.data.images:
    cand = os.path.join(clean_dir, img.name.replace(".", "_") + ".png")
    if os.path.exists(cand):
        new = bpy.data.images.load(cand)
        new.colorspace_settings.name = img.colorspace_settings.name
        img.user_remap(new)
        replaced.append(img.name)
for img in list(bpy.data.images):
    if img.users == 0:
        bpy.data.images.remove(img)
for img in bpy.data.images:
    w, h = img.size
    if max(w, h) > max_px:
        s = max_px / max(w, h)
        img.scale(max(1, int(w * s)), max(1, int(h * s)))
        img.pack()
    elif img.packed_file is None and img.filepath:
        img.pack()

tris_before = tris_after = 0
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    n = sum(len(p.vertices) - 2 for p in o.data.polygons)
    tris_before += n
    if ratio < 1.0 and n > 1500:
        m = o.modifiers.new("decimate", "DECIMATE")
        m.ratio = ratio
        m.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)
    tris_after += sum(len(p.vertices) - 2 for p in o.data.polygons)

if yaw:
    bpy.ops.object.empty_add(location=(0, 0, 0))
    root = bpy.context.active_object
    for o in bpy.data.objects:
        if o is not root and o.parent is None:
            o.parent = root
    root.rotation_euler[2] = math.radians(yaw)
    bpy.context.view_layer.update()

bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_apply=True, export_yup=True, export_cameras=False, export_lights=False, export_image_format="AUTO")
print("RESULT", {"replaced": replaced, "tris_before": tris_before, "tris_after": tris_after, "out": dst})
