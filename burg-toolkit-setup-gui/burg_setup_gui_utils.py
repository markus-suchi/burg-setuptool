import bpy
from enum import IntEnum
import os
import numpy as np
import mathutils
import matplotlib.pyplot as plt

import burg_toolkit as burg


class BurgStatus(IntEnum):
    OK = 0
    COLLISION = 1
    OUT_OF_BOUNDS = 2


BURG_STATUS_COLORS = {BurgStatus.OK: (0, 1, 0),
                      BurgStatus.COLLISION: (1, 0, 0),
                      BurgStatus.OUT_OF_BOUNDS: (1, 0, 1)}

BURG_PRINTOUT_SIZES = {"SIZE_A2": burg.constants.SIZE_A2,
                       "SIZE_A3": burg.constants.SIZE_A3,
                       "SIZE_A4": burg.constants.SIZE_A4}


def image_from_numpy(image, name="default"):
    """
    Converts numpy image to blender image

    :param: image as numpy array
    :param: name of the image in blender
    """
    h, w = np.shape(layout_img)
    byte_to_normalized = 1.0 / 255.0
    pil_image = Image.fromarray(layout_img)
    pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
    image = bpy.data.images.new("printout", alpha=False, width=w, height=h)
    image.pixels[:] = (np.asarray(pil_image.convert('RGBA'),
                       dtype=np.float32) * byte_to_normalized).ravel()
    image.file_format = 'PNG'
    return image


def get_size(size):
    return BURG_PRINTOUT_SIZES[size]


def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


@singleton
class SceneManager(object):
    """
    Manages access between burg objects and blender objects.

    """

    def __init__(self):
        self.blender_to_burg = {}
        self.object_library = None
        self.scene = None
        self.object_library_file = None

    def same_object_library(self, object_library_file=None):
        return self.object_library_file == object_library_file

    def load_object_library(self, filepath):
        """
        Loads and updates object library related interface items.

        :param filepath: Path to a object library yaml file
        """

        if not filepath or not os.path.isfile(filepath):
            raise ValueError(
                "Object Library File {object_lib_file} does not exist.")

        if self.same_object_library(filepath):
            return
        else:
            print("New object_library")
            self.object_library = burg.ObjectLibrary.from_yaml(filepath)
            print(self.object_library)
            self.object_library_file = filepath

    def random_scene(self, object_library_file=None, ground_area=burg.constants.SIZE_A3, n_instances=1, n_instances_objects=1):
        """
        Creates a random scene.

        :param object_library_file: Path to a object library yaml file
        :param ground_area: Size of the working area.
        :param n_instances: Number of object instances per scene.
        :param n_instances_objects: Number of instances per object.
        """

        self.load_object_library(object_library_file)

        if self.scene:
            print("removing current scene")

        # create the new scene
        self.scene = burg.sampling.sample_scene(
            object_library=self.object_library,
            ground_area=ground_area,
            instances_per_scene=n_instances,
            instances_per_object=n_instances_objects
        )

    def empty_scene(self, object_library_file=None, ground_area=burg.constants.SIZE_A3):
        """
        Creates an empty scene.

        :param object_library_file: Path to a object library yaml file
        :param ground_area: Size of the working area.
        """

        self.load_object_library(object_library_file)

        if self.scene:
            print("removing current scene")
            self.remove_blender_objects()

        self.scene = burg.core.Scene(ground_area=ground_area)

    def load_objects(self):
        """
        Loads objects from current scene into blender.
        """

        if not self.scene:
            return

        if "objects" not in bpy.data.collections:
            # deselect all
            bpy.ops.object.select_all(action='DESELECT')
            obj_collection = bpy.ops.collection.create(name="objects")
            bpy.context.scene.collection.children.link(
                bpy.data.collections["objects"])

        colormap = plt.get_cmap('tab20')
        color_idx = 0
        for i, item in enumerate(self.scene.objects):
            o3d_mesh = item.object_type.mesh
            pose = item.pose

            # TODO: Here we still make an name out of the type and not the instance
            blender_mesh = bpy.data.meshes.new(
                str(i) + '_' + item.object_type.identifier)
            blender_mesh.from_pydata(o3d_mesh.vertices, [], o3d_mesh.triangles)
            obj_id = i
            obj = bpy.data.objects.new(blender_mesh.name, blender_mesh)
            obj.matrix_world = mathutils.Matrix(pose)
            obj["burg_oid"] = obj_id
            obj["burg_status"] = BurgStatus.OK
            color_idx = (color_idx + 1) % colormap.N
            r, g, b = colormap(color_idx)[0:3]
            obj.color = (r, g, b, 1)
            obj["burg_color"] = (r, g, b, 1)
            # check if material for objects is there
            if not "burg_object_material" in bpy.data.materials:
                print("The material for displaying object colors is missing.")
            else:
                object_material = bpy.data.materials["burg_object_material"]
                # check if we already have appended the materials
                if len(obj.material_slots) < 1:  # if no materials on the object
                    obj.data.materials.append(object_material)

            bpy.data.collections["objects"].objects.link(obj)
            # create connection between scene and blender object
            self.blender_to_burg[obj] = item

    def check_status(self):
        """
        Checks the status of all object in the scene using simulation.
        """

        if not self.scene or "objects" not in bpy.data.collections:
            return

        collision_objects = self.scene.colliding_instances()
        out_of_bounds_objects = self.scene.out_of_bounds_instances()
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

    def update_scene_poses(self):
        """
        Updates poses of all object instances of current scene.
        """

        for key, value in self.blender_to_burg.items():
            value.pose[:, :] = key.matrix_world

    def update_blender_poses(self):
        """
        Updates poses of all blender objects from current scene.   
        """

        for key, value in self.blender_to_burg.items():
            key.matrix_world = mathutils.Matrix(value.pose)

    def remove_blender_objects(self):
        """
        Removes all blender objects and their meshes   
        """
        for key in self.blender_to_burg.keys():
            mesh = bpy.data.meshes[key.name]
            bpy.data.objects.remove(key, do_unlink=True)
            bpy.data.meshes.remove(mesh, do_unlink=True)

        self.blender_to_burg.clear()

    def simulate_scene(self, verbose=True):
        """
        Simulates current scene

        :param verbose: Visualize simulation. 
        """

        if not self.scene:
            return

        # TODO: Error handling
        # verbose shows the simulator GUI, slower than real-time
        sim = burg.scene_sim.SceneSimulator(verbose=verbose)
        # the poses of all instances in the scene are automatically updated by the simulator
        sim.simulate_scene(self.scene)
        sim.dismiss()  # can also reuse, then the window stays open

    def add_objects(self, id):
        """
        Adds an object with specific id to the scene and blender 

        :param id: Unique object identifier. 
        """

        print("adding object")

        if not self.scene:
            return

        if "objects" not in bpy.data.collections:
            # deselect all
            bpy.ops.object.select_all(action='DESELECT')
            obj_collection = bpy.ops.collection.create(name="objects")
            bpy.context.scene.collection.children.link(
                bpy.data.collections["objects"])

        # get new instance id
        instance_id = len(bpy.data.collections["objects"].objects)

        # create mesh if it is a new instance
        if self.object_library[id].stable_poses:
            stable_pose = self.object_library[id].stable_poses[0][1]
        else:
            stable_pose = np.eye(4)

        print(stable_pose)
        instance = burg.ObjectInstance(
            self.object_library[id], pose=stable_pose)

        # TODO: find better unique identifier for meshes
        mesh_id = f"burg_{id}"
        if bpy.data.meshes.get(mesh_id):
            print("Mesh is already there")
            blender_mesh = bpy.data.meshes.get(mesh_id)
        else:
            print(f"Create new Mesh for burg object {id}")
            o3d_mesh = instance.get_mesh()
            blender_mesh = bpy.data.meshes.new(mesh_id)
            blender_mesh.from_pydata(o3d_mesh.vertices, [], o3d_mesh.triangles)

        obj = bpy.data.objects.new(blender_mesh.name, blender_mesh)
        # TODO:  how to retrieve custom color
        obj.color = (155, 15, 0, 1)
        bpy.data.collections["objects"].objects.link(obj)
        self.blender_to_burg[obj] = instance
        obj["burg_oid"] = instance_id

    def lock_transform(self, enable=True):
        """
        Locks movement of objects: 
        Translation restricted to x-y plane.
        Rotation restricted to z axis.

        :param enable: Enable/Disable lock. 
        """

        for key in self.blender_to_burg.keys():
            if enable:
                key.lock_location[2] = True
                key.lock_rotation[0] = True
                key.lock_rotation[1] = True
            else:
                key.lock_location[2] = False
                key.lock_rotation[0] = False
                key.lock_rotation[1] = False

    def is_valid_scene(self):
        return self.scene or False

    def is_valid_object_library(self):
        return self.object_library or False


def update_display_colors(self, context):
    if "objects" in bpy.data.collections:
        burg_params = context.scene.burg_params
        if burg_params.view_mode == 'view_color':
            for o in bpy.data.collections["objects"].objects:
                o.color = o["burg_color"]
        elif burg_params.view_mode == 'view_state':
            for o in bpy.data.collections["objects"].objects:
                o.color[:3] = BURG_STATUS_COLORS[o["burg_status"]]


def trigger_display_update(params):
    if params.view_mode == 'view_state':
        params.view_mode = 'view_state'

# https://blender.stackexchange.com/questions/45138/buttons-for-custom-properties-dont-refresh-when-changed-by-other-parts-of-the-s
# Auto refresh for custom collection property does not work without tagging a redraw
def tag_redraw(context, space_type="PROPERTIES", region_type="WINDOW"):
    """ Redraws given windows area of specific type """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.spaces[0].type == space_type:
                for region in area.regions:
                    if region.type == region_type:
                        region.tag_redraw()
