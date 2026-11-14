"""Shared helpers for the procedural Blender models of the web viewer.

Run with Blender in background mode, e.g.
  blender --background --factory-startup --python scripts/blender/make_rover.py -- public/assets/models/rover.glb

Models are generic engineering shapes built from primitives: no agency logos, flags, mission
names or markings. Units are metres, +Y up after glTF export, the model faces +X (east at
yaw 0 in the viewer) unless stated.
"""
import math
import sys

import bpy

DEG = math.pi / 180


def out_path(default):
    argv = sys.argv
    return argv[argv.index("--") + 1] if "--" in argv and len(argv) > argv.index("--") + 1 else default


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            block.remove(item)


_MATS = {}


def mat(name, color, metal=0.0, rough=0.5, emit=None):
    """Principled material (exports as glTF metallic-roughness)."""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    _MATS[name] = m
    return m


def _finish(obj, material, name, parent, bevel, smooth):
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    if smooth:
        bpy.ops.object.shade_smooth_by_angle(angle=40 * DEG) if hasattr(bpy.ops.object, "shade_smooth_by_angle") else bpy.ops.object.shade_smooth()
    if parent:
        obj.parent = parent
    return obj


def box(name, size, loc, material, parent=None, rot=(0, 0, 0), bevel=0.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, material, name, parent, bevel, False)


def cyl(name, r, depth, loc, material, parent=None, rot=(0, 0, 0), verts=32, bevel=0.0, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    return _finish(o, material, name, parent, bevel, True)


def sphere(name, r, loc, material, parent=None, scale=(1, 1, 1), segs=32, half=False):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=segs, ring_count=segs // 2)
    o = bpy.context.active_object
    if half:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for v in o.data.vertices:
            v.select = v.co.z < -1e-4
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="VERT")
        bpy.ops.object.mode_set(mode="OBJECT")
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, material, name, parent, 0, True)


def torus(name, major, minor, loc, material, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=loc, rotation=rot, major_segments=40, minor_segments=12)
    o = bpy.context.active_object
    return _finish(o, material, name, parent, 0, True)


def empty(name, loc=(0, 0, 0), parent=None):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    o = bpy.context.active_object
    o.name = name
    if parent:
        o.parent = parent
    return o


def strut(name, a, b, r, material, parent=None):
    """Cylinder between points a and b (Blender Z-up coordinates)."""
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx - ax, by - ay, bz - az
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    o = cyl(name, r, length, ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2), material, parent, verts=12)
    o.rotation_mode = "QUATERNION"
    from mathutils import Vector

    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector((dx, dy, dz)).normalized())
    return o


def export_glb(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
        export_extras=False,
        export_cameras=False,
        export_lights=False,
    )
    print("EXPORTED", path)
