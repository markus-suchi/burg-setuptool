import bpy
from rna_prop_ui import rna_idprop_ui_prop_get

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


def add_material(blender_object):
    if not "burg_object_material" in bpy.data.materials:
        print("The material for displaying object colors is missing.")
    else:
        object_material = bpy.data.materials["burg_object_material"]
        # check if we already have appended the materials
        if len(blender_object.material_slots) < 1:  # if no materials on the object
            blender_object.data.materials.append(object_material)


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
        self.colormap = plt.get_cmap('tab20')
        self.instance_id = 0

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
            self.object_library = burg.ObjectLibrary.from_yaml(filepath)
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

        self.scene = burg.sampling.sample_scene(
            object_library=self.object_library,
            ground_area=ground_area,
            instances_per_scene=n_instances,
            instances_per_object=n_instances_objects
        )

        for item in self.scene.objects:
            self.add_burg_instance_to_blender(item)


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
            self.scene.objects.clear()

        self.scene = burg.core.Scene(ground_area=ground_area)
        #reset instance id
        self.instance_id = 0


    def check_status(self):
        """
        Checks the status of all object in the scene using simulation.
        """

        if not self.scene or "objects" not in bpy.data.collections:
            return

        collision_objects = self.scene.colliding_instances()
        out_of_bounds_objects = self.scene.out_of_bounds_instances()
        status_ok = True

        # check which objects in our map are in collision or out
        collision_instances = [self.scene.objects[i] for i in collision_objects]
        out_of_bounds_instances = [self.scene.objects[i] for i in out_of_bounds_objects]

        for key, value in self.blender_to_burg.items():
            real_object = bpy.data.objects[key]
            if value in collision_instances:
                real_object["burg_status"] = BurgStatus.COLLISION
                status_ok = False
            elif value in out_of_bounds_instances:
                real_object["burg_status"] = BurgStatus.OUT_OF_BOUNDS
                status_ok = False
            else:
                real_object["burg_status"] = BurgStatus.OK

        return status_ok

    def update_scene_poses(self):
        """
        Updates poses of all object instances of current scene.
        """

        for key, value in self.blender_to_burg.items():
            real_object = bpy.data.objects[key]
            self.blender_to_burg[key].pose[:, :] = real_object.matrix_world

    def update_blender_poses(self):
        """
        Updates poses of all blender objects from current scene.   
        """

        for key, value in self.blender_to_burg.items():
            real_object = bpy.data.objects[key]
            real_object.matrix_world = mathutils.Matrix(value.pose)

    def remove_blender_objects(self):
        """
        Removes all blender objects and their meshes   
        """

        for key in self.blender_to_burg.keys():
            obj = bpy.data.objects[key]
            mesh = bpy.data.meshes[obj.data.name]
            bpy.data.objects.remove(obj, do_unlink=True)
            # check if we are the last user for this mesh
            if mesh.users < 1:
                bpy.data.meshes.remove(mesh, do_unlink=True)

        self.blender_to_burg.clear()
        self.instance_id = 0

    def is_burg_object(self, obj):
        return obj.name in self.blender_to_burg.keys()

    def remove_object(self, obj):
        item = self.blender_to_burg.get(obj.name)
        if(item):
            self.blender_to_burg.pop(obj.name,None)
            self.scene.objects.remove(item)
            
            real_object = bpy.data.objects[obj.name]
            mesh = bpy.data.meshes[real_object.data.name]
            bpy.data.objects.remove(real_object, do_unlink=True)
            if mesh.users < 1:
                bpy.data.meshes.remove(mesh, do_unlink=True)

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

    def add_object(self, id):
        """
        Adds an object with specific id to the scene and blender 

        :param id: Unique burg ObjectType identifier. 
        """

        if not self.scene:
            return

         # retrieve first stable pose as default
        if self.object_library[id].stable_poses:
            stable_pose = self.object_library[id].stable_poses[0][1]
        else:
            stable_pose = np.eye(4)

        instance = burg.ObjectInstance(
            self.object_library[id], pose=stable_pose.copy())

        self.add_burg_instance_to_blender(instance)
        self.scene.objects.append(instance)


    def add_burg_instance_to_blender(self, instance):
        """
        Adds all relevant blender objects for a specific burg ObjectInstance 

        :param instance: A burg ObjectInstance 
        """

        if "objects" not in bpy.data.collections:
            # deselect all
            bpy.ops.object.select_all(action='DESELECT')
            obj_collection = bpy.ops.collection.create(name="objects")
            bpy.context.scene.collection.children.link(
                bpy.data.collections["objects"])


        mesh_id = f"{instance.object_type.identifier}"
        if bpy.data.meshes.get(mesh_id):
            blender_mesh = bpy.data.meshes.get(mesh_id)
        else:
            o3d_mesh = instance.object_type.mesh
            blender_mesh = bpy.data.meshes.new(mesh_id)
            blender_mesh.from_pydata(o3d_mesh.vertices, [], o3d_mesh.triangles)

        obj = bpy.data.objects.new(
            f"{hash(instance)}", blender_mesh)
        bpy.data.collections["objects"].objects.link(obj)
        color = self.get_color(hash(instance))
        obj["burg_oid"] = str(hash(instance))
        obj["burg_color"] = color
        obj["burg_status"] = BurgStatus.OK
        # create the list of possible stable poses for this instance
        cc_pose = len(get_stable_poses(instance))
        obj.burg_stable_poses = 0
        if cc_pose:
            # from https://blender.stackexchange.com/questions/143975/how-to-edit-a-custom-property-in-a-python-script
            # restrict poses to available poses
            ui = rna_idprop_ui_prop_get(obj, "burg_stable_poses", create=True)
            ui['min'] = ui['soft_min'] = 0
            ui['max'] = ui['soft_max'] = cc_pose-1
            for area in bpy.context.screen.areas:
                    area.tag_redraw()

        obj.matrix_world = mathutils.Matrix(instance.pose)
        obj.color = color
        add_material(obj)
        self.blender_to_burg[obj.name] = instance
        self.instance_id += 1

    def set_to_stable_pose(self, obj):
        print("set_to_stable_pose")
        if self.has_stable_poses(obj):
            print("has stable_pose")
            idx = obj.burg_stable_poses
            instance = self.blender_to_burg.get(obj.name)
            
            if instance:
                new_pose = mathutils.Matrix(instance.object_type.stable_poses[idx][1].copy())
                new_pose[0][3] = obj.matrix_world[0][3]
                new_pose[1][3] = obj.matrix_world[1][3]
                obj.matrix_world = new_pose
                for area in bpy.context.screen.areas:
                        area.tag_redraw()



    def lock_transform(self, enable=True):
        """
        Locks movement of objects: 
        Translation restricted to x-y plane.
        Rotation restricted to z axis.

        :param enable: Enable/Disable lock. 
        """

        for key in self.blender_to_burg.keys():
            obj = bpy.data.objects[key]
            if enable:
                obj.lock_location[2] = True
                obj.lock_rotation[0] = True
                obj.lock_rotation[1] = True
            else:
                obj.lock_location[2] = False
                obj.lock_rotation[0] = False
                obj.lock_rotation[1] = False

    def is_valid_scene(self):
        return self.scene or False

    def is_valid_object_library(self):
        return self.object_library or False

    def has_stable_poses(self, obj):
        instance = self.blender_to_burg.get(obj.name)
        if instance:
            return bool(instance.object_type.stable_poses)
        else:
            return False
    
    def get_stable_poses(self, obj):
        instance = self.blender_to_burg.get(obj.name)
        if instance:
            return instance.object_type.stable_poses
        else:
            return None 


    def get_color(self, id):
        id = (id) % self.colormap.N
        r, g, b = self.colormap(id)[0:3]
        return (r, g, b, 1)

    def get_burg_instance(self, obj):
        instance = self.blender_to_burg.get(obj.name)
        if instance:
            return instance
        else:
            return None

    
def get_stable_poses(instance):
        stable_poses = []
        for pose in instance.object_type.stable_poses:
            new_pose = pose[1].copy()
            new_pose[0,3]=0
            new_pose[1,3]=0
            stable_poses.append(mathutils.Matrix(new_pose))

        return stable_poses


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


def tag_redraw(context, space_type="PROPERTIES", region_type="WINDOW"):
    # https://blender.stackexchange.com/questions/45138/buttons-for-custom-properties-dont-refresh-when-changed-by-other-parts-of-the-s
    # Auto refresh for custom collection property does not work without tagging a redraw
    """ Redraws given windows area of specific type """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.spaces[0].type == space_type:
                for region in area.regions:
                    if region.type == region_type:
                        region.tag_redraw()
