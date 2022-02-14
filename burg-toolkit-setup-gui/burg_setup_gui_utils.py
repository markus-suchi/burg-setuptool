import bpy
import addon_utils

from enum import IntEnum
import os
import numpy as np
import mathutils
import matplotlib.pyplot as plt
from PIL import Image

import burg_toolkit as burg


class BurgStatus(IntEnum):
    OK = 0
    COLLISION = 1
    OUT_OF_BOUNDS = 2


BURG_STATUS_COLORS = {BurgStatus.OK: (0, 1, 0),
                      BurgStatus.COLLISION: (1, 0, 0),
                      BurgStatus.OUT_OF_BOUNDS: (1, 0, 1)}

BLENDER_TO_BURG_SIZES = {"SIZE_A2": burg.constants.SIZE_A2,
                         "SIZE_A3": burg.constants.SIZE_A3,
                         "SIZE_A4": burg.constants.SIZE_A4}

BURG_TO_BLENDER_SIZES = {burg.constants.SIZE_A2: "SIZE_A2",
                         burg.constants.SIZE_A3: "SIZE_A3",
                         burg.constants.SIZE_A4: "SIZE_A4"}


def get_resources_folder():
    for mod in addon_utils.modules():
        if mod.bl_info['name'] == "BURG toolkit - Setup GUI":
            file = mod.__file__
            return os.path.join(os.path.dirname(file), 'resources')
        else:
            pass


def convert_numpy_image(image):
    """
    Converts numpy image to blender image

    :param: image as numpy array
    :return blender ready pixel array
    """

    h, w = np.shape(image)
    byte_to_normalized = 1.0 / 255.0
    pil_image = Image.fromarray(image)
    pil_image = pil_image.transpose(Image.FLIP_TOP_BOTTOM)
    return (np.asarray(pil_image.convert('RGBA'),
                       dtype=np.float32) * byte_to_normalized).ravel()


def add_material(blender_object):
    if not "burg_object_material" in bpy.data.materials:
        print("The material for displaying object colors is missing.")
    else:
        object_material = bpy.data.materials["burg_object_material"]
        # check if we already have appended the materials
        if len(blender_object.material_slots) < 1:  # if no materials on the object
            blender_object.data.materials.append(object_material)


def get_size(size):
    return BLENDER_TO_BURG_SIZES[size]


def get_stable_poses(instance):
    stable_poses = []
    for pose in instance.object_type.stable_poses:
        new_pose = pose[1].copy()
        new_pose[0, 3] = 0
        new_pose[1, 3] = 0
        stable_poses.append(mathutils.Matrix(new_pose))

    return stable_poses


def update_display_colors():
    burg_params = bpy.context.scene.burg_params
    burg_objects = [o for o in bpy.data.objects if o.get("burg_object_type")]
    if burg_params.view_mode == 'view_color':
        for o in burg_objects:
            o.color = o["burg_color"]
    elif burg_params.view_mode == 'view_state':
        for o in burg_objects:
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


def set_active_and_select(obj):
    bpy.context.view_layer.objects.active = obj
    for selected in bpy.context.selected_objects:
        selected.select_set(False)
    obj.select_set(True)


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
        self.color_id = 0

    def same_object_library(self, object_library_file=None):
        return self.object_library_file == object_library_file

    def set_area_size(self, size):
        self.scene.ground_area = get_size(size)

    def complete_object_library(self, savepath):
        lib = self.object_library

        if lib and not lib.objects_have_all_attributes():
            lib.generate_vhacd_files(override=False)
            lib.generate_urdf_files(override=False, use_vhacd=True)
            lib.compute_stable_poses(verify_in_sim=True, override=False)
            engine = burg.render.RenderEngineFactory.create('pybullet')
            lib.generate_thumbnails(render_engine=engine, override=False)
            engine.dismiss()
            lib.to_yaml(savepath)

    def load_object_library(self, filepath, savepath=None):
        """
        Loads and updates object library related interface items.

        :param filepath: Path to a object library yaml file
        """

        if not filepath or not os.path.isfile(filepath):
            raise ValueError(
                f"Object Library File {filepath} does not exist.")

        # If no savepath is given we override and use filepath
        if not savepath:
            savepath = filepath

        if not self.same_object_library(filepath):
            self.object_library = burg.ObjectLibrary.from_yaml(filepath)
            self.complete_object_library(savepath)
            self.object_library.filepath = savepath
            self.object_library_file = savepath
        # Loading a new object_library invalidates the scene and mapping
        self.blender_to_burg.clear()
        self.scene = None

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
            self.remove_blender_objects()
            self.scene.objects.clear()

        self.scene = burg.sampling.sample_scene(
            object_library=self.object_library,
            ground_area=ground_area,
            instances_per_scene=n_instances,
            instances_per_object=n_instances_objects
        )

        self.color_id = 0

        for item in self.scene.objects:
            self.add_burg_instance_to_blender(item)

    def empty_scene(self, object_library_file=None, ground_area=burg.constants.SIZE_A3, savepath=None):
        """
        Creates an empty scene.

        :param object_library_file: Path to a object library yaml file
        :param ground_area: Size of the working area.
        """

        self.load_object_library(object_library_file, savepath=savepath)

        if self.scene:
            self.remove_blender_objects()
            self.scene.objects.clear()

        self.scene = burg.core.Scene(ground_area=ground_area)
        self.color_id = 0

    def load_scene(self, scene_file=None, savepath=None):
        """
        Loads a scene from file.

        :param scene_file: Path to a scene yaml file
        """

        if not os.path.isfile(scene_file):
            print(f"The scene file {scene_file} does not exist.")
        else:
            try:
                self.remove_blender_objects()
                scene, library, printout = burg.Scene.from_yaml(scene_file)
                self.load_object_library(library.filename, savepath=savepath)
                scene, library, printout = burg.Scene.from_yaml(
                    scene_file, object_library=self.object_library)
                if scene and library:
                    if self.scene:
                        self.scene.objects.clear()
                    self.scene = scene
                    self.scene.object_library = self.object_library
                    self.blender_to_burg.clear()
                    for item in self.scene.objects:
                        self.add_burg_instance_to_blender(item)
            except Exception as e:
                print(f"Could not open burg scene: {scene_file}")
                print(e)

    def save_scene(self, scene_file=None):
        if scene_file:
            try:
                # create a printout with current settings
                self.scene.to_yaml(scene_file, self.object_library)
            except Exception as e:
                print(f"Could not save burg scene: {scene_file}")
                print(e)

    def check_status(self):
        """
        Checks the status of all object in the scene using simulation.
        """

        if not self.scene:
            return False

        collision_objects = self.scene.colliding_instances()
        out_of_bounds_objects = self.scene.out_of_bounds_instances()
        status_ok = True

        # check which objects in our map are in collision or out
        collision_instances = [self.scene.objects[i]
                               for i in collision_objects]
        out_of_bounds_instances = [self.scene.objects[i]
                                   for i in out_of_bounds_objects]

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
            # The blender object can be deleted before an update to the blender_to_burg map during Undo/Redo actions
            # Therfore no remove is necessary
            if key in bpy.data.objects.keys():
                obj = bpy.data.objects[key]
                mesh = bpy.data.meshes[obj.data.name]
                bpy.data.objects.remove(obj, do_unlink=True)
                # check if we are the last user for this mesh
                if mesh.users < 1:
                    bpy.data.meshes.remove(mesh, do_unlink=True)

        self.blender_to_burg.clear()
        self.color_id = 0

    def is_burg_object(self, obj):
        return obj.name in self.blender_to_burg.keys()

    def remove_object(self, obj):
        item = self.blender_to_burg.get(obj.name)
        if(item):
            self.blender_to_burg.pop(obj.name, None)
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
            return None

         # retrieve first stable pose as default
        if self.object_library[id].stable_poses:
            stable_pose = self.object_library[id].stable_poses[0][1]
        else:
            stable_pose = np.eye(4)

        instance = burg.ObjectInstance(
            self.object_library[id], pose=stable_pose.copy())

        self.scene.objects.append(instance)
        return self.add_burg_instance_to_blender(instance)

    def add_burg_instance_to_blender(self, instance):
        """
        Adds all relevant blender objects for a specific burg ObjectInstance 

        :param instance: A burg ObjectInstance 
        """

        mesh_id = f"{instance.object_type.identifier}"
        if bpy.data.meshes.get(mesh_id):
            blender_mesh = bpy.data.meshes.get(mesh_id)
        else:
            o3d_mesh = instance.object_type.mesh
            blender_mesh = bpy.data.meshes.new(mesh_id)
            blender_mesh.from_pydata(o3d_mesh.vertices, [], o3d_mesh.triangles)

        obj = bpy.data.objects.new(
            f"{hash(instance)}", blender_mesh)
        self.color_id += 1
        color = self.get_color(self.color_id)
        obj["burg_color"] = color
        obj["burg_status"] = BurgStatus.OK
        obj["burg_object_type"] = instance.object_type.identifier
        # TODO: A bug in blender if rotation mode is set to Euler some very small rotation is 
        # added in blender
        # This can be verified by switching between QUATERNION and XYZ rotation mode
        # in blender. The switching alone can cause rotation for some objects
        # obj.rotation_mode = 'QUATERNION'
        obj.matrix_world = mathutils.Matrix(instance.pose)
        obj.color = color
        add_material(obj)
        self.blender_to_burg[obj.name] = instance
        bpy.context.collection.objects.link(obj)
        return obj

    def set_to_stable_pose(self, obj):
        if self.has_stable_poses(obj):
            idx = obj.burg_stable_poses
            instance = self.blender_to_burg.get(obj.name)

            if instance:
                new_pose = mathutils.Matrix(
                    instance.object_type.stable_poses[idx][1].copy())
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
            # always lock scaling
            obj.lock_scale = [True, True, True]
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
        return self.blender_to_burg.get(obj.name)

    def synchronize(self):
        try:
            if self.scene:
                key = set(self.blender_to_burg.keys())
                active = {obj.name
                          for obj in bpy.data.objects if obj.get("burg_object_type")}
                delete = key - active
                add = active - key

                for item in delete:
                    instance = self.blender_to_burg.pop(item, None)
                    if instance:
                        self.scene.objects.remove(instance)

                for item in add:
                    # get current pose from blender object
                    obj = bpy.data.objects[item]
                    blender_pose = np.eye(4)
                    blender_pose[:, :] = obj.matrix_world
                    # create the instance and set to new pose
                    instance = burg.ObjectInstance(self.object_library[obj["burg_object_type"]],
                                                   pose=blender_pose.copy())
                    self.scene.objects.append(instance)
                    self.blender_to_burg[item] = instance
                    # needs a new color
                    self.color_id += 1
                    obj["burg_color"] = self.get_color(self.color_id)

                update_display_colors()

                size = get_size(bpy.context.scene.burg_params.area_size)
                if not self.scene.ground_area == size:
                    self.scene.ground_area = size

                    # To trigger update callback we have to reset this value
                    size = bpy.context.scene.burg_params.area_size
                    bpy.context.scene.burg_params.area_size = size

            for area in bpy.context.screen.areas:
                area.tag_redraw()
        except Exception as e:
            print("Error during synchronize.")
            print(e)
