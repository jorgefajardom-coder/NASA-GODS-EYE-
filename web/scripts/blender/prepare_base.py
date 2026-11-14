"""Prepare the owner's Mars base model for the viewer (public/assets/models/base.glb).

Input: the owner-supplied ``base-marciana-v2.blend`` (kept as ``scripts/blender/source/``).
The model is edited for the mission viewer, deterministically:

1. Its own ground (``Terreno ·``) and rocks (``Rocas ·``) are removed: the viewer draws the
   real CTX terrain of Jezero instead.
2. Realism pass: matte thermal cladding, a dust tint that fades from the ground up (vertex
   colours), solar panels turned to face the equator (south at 18 N), regolith sandbag
   berms against the modules (radiation shielding), two thermal radiators, a comms mast
   with a dish and power cables from the solar field to the hub.
3. Export as GLB with +Y up. Blender axes are local ENU around the hub (x east, y north,
   z up), so glTF gives x east, y up, z = -north. Origin on the ground at the hub centre.

No textures, no agency logos, flags or mission marks.

Usage (from web/):
  blender -b scripts/blender/source/base-marciana-v2.blend --python scripts/blender/prepare_base.py -- public/assets/models/base.glb [preview.png]
"""
import math
import sys

import bmesh
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else None
PREVIEW = argv[1] if len(argv) > 1 else None

DUST = (0.62, 0.40, 0.28)   # multiplier at the ground: reddish dust film
DUST_HEIGHT_M = 1.6         # fades to clean above this height
ADDED = 'Base · Detalle'    # name prefix of the parts this script adds


def mat(name, color, rough, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    return link(bpy.data.objects.new(name, me))


def box(name, material, size, loc, rot_z=0.0, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES')
    o = mesh_obj(name, bm, material)
    o.location, o.rotation_euler = loc, (0, 0, rot_z)
    return o


def cyl(name, material, r, depth, loc, rot=(0, 0, 0), segs=16, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    o = mesh_obj(name, bm, material)
    o.location, o.rotation_euler = loc, rot
    return o


def world_bbox(objs):
    """Axis-aligned bounds of the actual vertices (object bound boxes overestimate tilted, scaled parts)."""
    xs, ys, zs = [], [], []
    for o in objs:
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            xs.append(p.x)
            ys.append(p.y)
            zs.append(p.z)
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def group(prefix):
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith(prefix)]


# ------------------------------------------------------------------ 1. strip ground and rocks
for o in list(bpy.data.objects):
    if o.type == 'MESH' and (o.name.startswith('Terreno') or o.name.startswith('Rocas')):
        bpy.data.objects.remove(o, do_unlink=True)
for o in list(bpy.data.objects):
    if o.name.startswith(ADDED):
        bpy.data.objects.remove(o, do_unlink=True)

# ------------------------------------------------------------------ 2a. materials
cladding = bpy.data.materials.get('Revestimiento térmico')
if cladding:
    b = cladding.node_tree.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.82  # beta-cloth / painted panels, not glossy plastic
alloy = bpy.data.materials.get('Aleación anodizada')
if alloy:
    alloy.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.55
SANDBAG = mat('Sacos de regolito', (0.36, 0.20, 0.11), 0.95)
RADIATOR = mat('Radiador', (0.80, 0.80, 0.78), 0.35, 0.1)
CABLE = mat('Cable', (0.03, 0.03, 0.03), 0.6)
WHITE = cladding or mat('Blanco', (0.68, 0.65, 0.56), 0.82)
METAL = alloy or mat('Metal', (0.22, 0.24, 0.24), 0.55, 0.45)

# ------------------------------------------------------------------ 2b. solar panels face south
solar = group('Campo solar')
cells = [o for o in solar if 'Celdas' in o.name]
facing = Vector((0, 0, 0))
for o in cells:
    nm = o.matrix_world.to_3x3().inverted().transposed()  # normals under non-uniform scale
    for p in o.data.polygons:
        n = (nm @ p.normal).normalized()
        if n.z > 0.3:  # top faces only; the backs would cancel them
            facing += n * p.area
if facing.y > 0.05 * facing.length:  # tilted toward the north: turn the field 180 deg in place
    lo, hi = world_bbox(solar)
    pivot = (lo + hi) / 2
    for o in solar:
        o.location = pivot + Vector((-(o.location.x - pivot.x), -(o.location.y - pivot.y), o.location.z - pivot.z))
        o.rotation_euler.z += math.pi
print('solar facing before', tuple(round(v, 2) for v in facing.normalized()))

# ------------------------------------------------------------------ 2c. added details
modules = group('Módulo')
mlo, mhi = world_bbox(modules)
hub_lo, hub_hi = world_bbox(group('Núcleo'))
slo, shi = world_bbox(solar)
added = []

# Regolith sandbag berm, two courses, along the north side and both ends of the module block.
def berm(x0, y0, x1, y1):
    length = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - y0, x1 - x0)
    n = max(1, int(length / 0.85))
    for course in range(2):
        for i in range(n - course):
            t = (i + 0.5 + course * 0.5) / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            added.append(box(f'{ADDED} · berma', SANDBAG, (0.8, 0.5, 0.3), (x, y, 0.15 + 0.28 * course), ang + 0.04 * ((i % 3) - 1), bevel=0.07))

pad = 0.9
berm(mlo.x - pad, mhi.y + pad, mhi.x + pad, mhi.y + pad)
berm(mlo.x - pad, mlo.y + 1.5, mlo.x - pad, mhi.y + pad)
berm(mhi.x + pad, mlo.y + 1.5, mhi.x + pad, mhi.y + pad)

# Two vertical thermal radiators south of the hub, edge-on to the noon sun.
for sx in (-1, 1):
    x, y = sx * 2.6, hub_lo.y - 3.2
    added.append(box(f'{ADDED} · radiador', RADIATOR, (0.06, 3.0, 1.8), (x, y, 1.6)))
    for dy in (-1.3, 1.3):
        added.append(box(f'{ADDED} · soporte', METAL, (0.12, 0.12, 0.7), (x, y + dy, 0.35)))
    added.append(cyl(f'{ADDED} · tuberia', METAL, 0.06, abs(y) - 3.4, (x * 0.6, y / 2 - 1.6, 0.25), rot=(math.pi / 2, 0, 0), segs=8))

# Comms mast with a dish, west of the module block.
mx, my = mlo.x - 3.5, (mlo.y + mhi.y) / 2
added.append(cyl(f'{ADDED} · mastil', METAL, 0.09, 7.0, (mx, my, 3.5), segs=10, r2=0.06))
added.append(cyl(f'{ADDED} · base mastil', METAL, 0.5, 0.25, (mx, my, 0.125), segs=16))
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=8, radius=0.9)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > -0.45], context='VERTS')
dish = mesh_obj(f'{ADDED} · antena', bm, RADIATOR)
dish.location, dish.rotation_euler = (mx + 0.3, my, 6.6), (0, math.radians(-120), 0)
added.append(dish)
for a in range(3):  # guy lines
    t = math.radians(120 * a + 30)
    gx, gy = mx + 2.4 * math.cos(t), my + 2.4 * math.sin(t)
    d = Vector((mx - gx, my - gy, 5.0))
    o = cyl(f'{ADDED} · tensor', CABLE, 0.012, d.length, ((mx + gx) / 2, (my + gy) / 2, 2.5), segs=4)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    added.append(o)

# Power cables lying on the ground from the solar field to the hub.
for k, off in enumerate((-0.25, 0.25)):
    a = Vector((slo.x, (slo.y + shi.y) / 2 + off, 0.05))
    b = Vector((hub_hi.x + 0.2, off, 0.05))
    d = b - a
    o = cyl(f'{ADDED} · cable', CABLE, 0.04, d.length, (a + b) / 2, segs=6)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    added.append(o)

# ------------------------------------------------------------------ 2d. dust film (vertex colours)
bpy.context.view_layer.update()  # world matrices of the parts added above
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    me = o.data
    attr = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    me.color_attributes.active_color = attr
    mw = o.matrix_world
    for i, v in enumerate(me.vertices):
        z = (mw @ v.co).z
        t = max(0.0, min(1.0, z / DUST_HEIGHT_M))
        t = t * t * (3 - 2 * t)
        attr.data[i].color = (DUST[0] + (1 - DUST[0]) * t, DUST[1] + (1 - DUST[1]) * t, DUST[2] + (1 - DUST[2]) * t, 1.0)
# Show the film in Blender renders too (glTF takes it from COLOR_0 regardless).
for m in bpy.data.materials:
    if not m.use_nodes or 'Principled BSDF' not in m.node_tree.nodes or m.node_tree.nodes.get('dust_mul'):
        continue
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    ca = nt.nodes.new('ShaderNodeVertexColor')
    ca.layer_name = 'Col'
    mix = nt.nodes.new('ShaderNodeMix')
    mix.name = 'dust_mul'
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    mix.inputs[6].default_value = bsdf.inputs['Base Color'].default_value
    nt.links.new(ca.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])

meshes = [o for o in bpy.data.objects if o.type == 'MESH']
lo, hi = world_bbox(meshes)
for o in meshes:
    olo, ohi = world_bbox([o])
    if olo.z < -0.25:
        print('BELOW GROUND', o.name, round(olo.z, 2), round(ohi.z, 2))
print('footprint m', tuple(round(v, 2) for v in (hi - lo)), 'min z', round(lo.z, 3), 'added', len(added))

# ------------------------------------------------------------------ 3. export / preview
if OUT:
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
        export_vertex_color='ACTIVE', export_cameras=False, export_lights=False, export_extras=False,
    )
if PREVIEW:
    sc = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 0, 0))
    g = bpy.context.active_object
    g.data.materials.append(mat('preview ground', (0.30, 0.15, 0.08), 1.0))
    cam = sc.camera or link(bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera')))
    sc.camera = cam
    cam.location = (-26, -34, 22)
    cam.rotation_euler = (Vector((2, 2, 1)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 32
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1440, 900, 100
    sc.render.filepath = PREVIEW
    bpy.ops.render.render(write_still=True)
