"""Blender (background) render of the carrier, with or without the Portenta H7.
blender -b -P render.py -- DIR MODE OUT.png   (MODE: assembled | carrier)"""
import sys, math, os
import bpy, bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
D, MODE, OUT = argv[0], argv[1], argv[2]
W, H, T = 68.0, 40.0, 1.6

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'


def principled(name, rgb, rough=0.45, metal=0.0, tex=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if tex:
        img = bpy.data.images.load(os.path.join(D, tex))
        n = m.node_tree.nodes.new('ShaderNodeTexImage')
        n.image = img
        m.node_tree.links.new(n.outputs['Color'], b.inputs['Base Color'])
    return m


# board slab with textured top / bottom faces
mesh = bpy.data.meshes.new('board')
bm = bmesh.new()
v = [bm.verts.new(p) for p in [(0, -H, 0), (W, -H, 0), (W, 0, 0), (0, 0, 0), (0, -H, T), (W, -H, T), (W, 0, T), (0, 0, T)]]
faces = [((4, 5, 6, 7), 0), ((3, 2, 1, 0), 1), ((0, 1, 5, 4), 2), ((1, 2, 6, 5), 2), ((2, 3, 7, 6), 2), ((3, 0, 4, 7), 2)]
uv = bm.loops.layers.uv.new('UVMap')
for idx, mi in faces:
    f = bm.faces.new([v[i] for i in idx])
    f.material_index = mi
    for loop in f.loops:
        co = loop.vert.co
        loop[uv].uv = (co.x / W, (co.y + H) / H)
bm.to_mesh(mesh)
bm.free()
board = bpy.data.objects.new('board', mesh)
scene.collection.objects.link(board)
mesh.materials.append(principled('top', (0, 0, 0), rough=0.35, tex='tex_F.png'))
mesh.materials.append(principled('bottom', (0, 0, 0), rough=0.35, tex='tex_B.png'))
mesh.materials.append(principled('edge', (0.08, 0.09, 0.08), rough=0.6))


def import_obj(name):
    bpy.ops.wm.obj_import(filepath=os.path.join(D, name), forward_axis='Y', up_axis='Z')
    for o in bpy.context.selected_objects:
        for slot in o.material_slots:
            m = slot.material
            if not m or not m.use_nodes:
                continue
            b = m.node_tree.nodes.get('Principled BSDF')
            if not b:
                continue
            nm = m.name.lower()
            if 'metal' in nm:
                b.inputs['Metallic'].default_value = 0.9
                b.inputs['Roughness'].default_value = 0.28
            elif 'pcb_h7' in nm:
                b.inputs['Roughness'].default_value = 0.3
            elif 'ceramic' in nm or 'nylon' in nm or 'plastic' in nm:
                b.inputs['Roughness'].default_value = 0.55
            else:
                b.inputs['Roughness'].default_value = 0.4


import_obj('carrier_parts.obj')
if MODE == 'assembled':
    import_obj('h7_blocks.obj')

# shadow catcher floor (carrier stands on 4 mm feet so bottom parts clear it)
bpy.ops.mesh.primitive_plane_add(size=600, location=(W / 2, -H / 2, -4.0))
floor = bpy.context.active_object
floor.is_shadow_catcher = True

# lights
def area(name, loc, energy, size):
    l = bpy.data.lights.new(name, 'AREA')
    l.energy = energy
    l.size = size
    o = bpy.data.objects.new(name, l)
    o.location = loc
    scene.collection.objects.link(o)
    d = Vector((W / 2, -H / 2, 0)) - o.location
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


area('key', (-40, -110, 120), 5.5e5, 90)
area('fill', (140, -20, 70), 1.4e5, 80)
area('rim', (30, 90, 60), 2.5e5, 60)
scene.world = bpy.data.worlds.new('w')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.9, 0.92, 0.95, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.12

# camera
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
scene.collection.objects.link(cam)
cam.data.lens = 85
cam.location = (-70, -175, 135) if MODE == 'assembled' else (-60, -165, 145)
target = Vector((W / 2, -H / 2, 3.0))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam

scene.render.engine = 'CYCLES'
scene.cycles.samples = 160
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x, scene.render.resolution_y = 1800, 1150
scene.render.filepath = OUT
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.view_settings.view_transform = 'AgX'
try:
    scene.view_settings.look = 'AgX - Punchy'
except TypeError:
    pass

# frame the board: fit camera distance so the whole model fills ~85 % of the width
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='SELECT')
floor.select_set(False)
bpy.ops.view3d.camera_to_view_selected() if False else None
bpy.ops.render.render(write_still=True)
print('rendered', OUT)
