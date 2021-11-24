import bpy
from enum import IntEnum
import os
import numpy as np
import mathutils
import matplotlib.pyplot as plt

import burg_toolkit as burg

dim = (0.594, 0.42)


class BurgStatus(IntEnum):
    OK = 0
    COLLISION = 1
    OUT_OF_BOUNDS = 2


BURG_STATUS_COLORS = {BurgStatus.OK: (0, 1, 0),
                      BurgStatus.COLLISION: (1, 0, 0),
                      BurgStatus.OUT_OF_BOUNDS: (1, 0, 1)}


def create_scene(object_library, n_instances=1, n_instances_objects=1):
    # TODO: Error handling
    scene = burg.sampling.sample_scene(
        object_library,
        ground_area=dim,
        instances_per_scene=n_instances,
        instances_per_object=n_instances_objects
    )
    return scene


def load_objects(scene):
    if "objects" not in bpy.data.collections:
        # deselect all
        bpy.ops.object.select_all(action='DESELECT')
        obj_collection = bpy.ops.collection.create(name="objects")
        bpy.context.scene.collection.children.link(
            bpy.data.collections["objects"])

    colormap = plt.get_cmap('tab20')
    color_idx = 0
    for i, item in enumerate(scene.objects):
        o3d_mesh = item.object_type.mesh
        pose = item.pose
        blender_mesh = bpy.data.meshes.new(
            str(i) + '_' + item.object_type.identifier)
        blender_mesh.from_pydata(o3d_mesh.vertices, [], o3d_mesh.triangles)
        obj_id = i
        obj = bpy.data.objects.new(blender_mesh.name, blender_mesh)
        obj.matrix_world = mathutils.Matrix(pose)
        r, g, b = colormap(color_idx)[0:3]
        obj.color = (r, g, b, 1)
        bpy.data.collections["objects"].objects.link(obj)
        color_idx = (color_idx + 1) % colormap.N
        obj["burg_oid"] = obj_id
        obj["burg_status"] = BurgStatus.OK
        obj["burg_color"] = (r, g, b, 1)
        # check if material for objects is there
        if not "burg_object_material" in bpy.data.materials:
            print("The material for displaying object colors is missing.")
        else:
            object_material = bpy.data.materials["burg_object_material"]
            for o in bpy.data.collections["objects"].objects:
                # check if we already have appended the materials
                if len(o.material_slots) < 1:  # if no materials on the object
                    o.data.materials.append(object_material)


def check_status(scene):
    collision_objects = scene.colliding_instances()
    out_of_bounds_objects = scene.out_of_bounds_instances()
    status_ok = True
    for o in bpy.data.collections["objects"].objects:
        if o["burg_oid"] in collision_objects:
            o["burg_status"] = BurgStatus.COLLISION
            status_ok = False
        elif o["burg_oid"] in out_of_bounds_objects:
            o["burg_status"] = BurgStatus.OUT_OF_BOUNDS
            status_ok = False
        else:
            o["burg_status"] = BurgStatus.OK
    return status_ok

def update_scene(scene):
    for o in bpy.data.collections["objects"].objects:
        obj_id = o["burg_oid"]
        pose = np.zeros((4, 4))
        pose[:, :] = o.matrix_world
        burg_object = scene.objects[obj_id]
        burg_object.pose = pose


def update_objects(scene):
    for o in bpy.data.collections["objects"].objects:
        obj_id = o["burg_oid"]
        o.matrix_world = mathutils.Matrix(scene.objects[obj_id].pose)


def remove_objects():
    # TODO: do not reimport already loaded objects, just reset position
    if "objects" in bpy.data.collections:
        for o in bpy.data.collections["objects"].objects:
            m = bpy.data.meshes[o.name]
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(m, do_unlink=True)


def simulate_scene(scene, verbose=True):
    # TODO: Error handling
    # verbose shows the simulator GUI, slower than real-time
    sim = burg.scene_sim.SceneSimulator(verbose=verbose)
    # the poses of all instances in the scene are automatically updated by the simulator
    sim.simulate_scene(scene)
    sim.dismiss()  # can also reuse, then the window stays open


def update_lock_transform(self, context):
    burg_params = context.scene.burg_params
    for o in bpy.data.collections["objects"].objects:
        if burg_params.lock_transform:
            o.lock_location[2] = True
            o.lock_rotation[0] = True
            o.lock_rotation[1] = True
        else:
            o.lock_location[2] = False
            o.lock_rotation[0] = False
            o.lock_rotation[1] = False


def update_display_colors(self, context):
    if "objects" in bpy.data.collections:
        burg_params = context.scene.burg_params
        if burg_params.view_mode == 'view_color':
            print("view color")
            for o in bpy.data.collections["objects"].objects:
                print("setting color")
                o.color = o["burg_color"]
        elif burg_params.view_mode == 'view_state':
            for o in bpy.data.collections["objects"].objects:
                o.color[:3] = BURG_STATUS_COLORS[o["burg_status"]]


def trigger_display_update(params):
    if params.view_mode == 'view_state':
        params.view_mode = 'view_state'
