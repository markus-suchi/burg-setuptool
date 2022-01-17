from bpy.app.handlers import persistent
import bpy.utils.previews
import bpy
import mathutils

import burg_toolkit as burg
import burg_setup_gui_utils as utils

import os
import numpy as np
import traceback

# the one and only manager
mng = utils.SceneManager()


# SCENE OPERATORS
class BURG_OT_random_scene(bpy.types.Operator):
    """ Creates a random scene """

    bl_idname = "burg.random_scene"
    bl_label = "Create Random Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.context.window.cursor_set("WAIT")
        burg_params = context.scene.burg_params
        mng.remove_blender_objects()
        mng.random_scene(burg_params.object_library_file,
                         n_instances=burg_params.number_objects,
                         ground_area=utils.get_size(
                             burg_params.area_size),
                         n_instances_objects=burg_params.number_instances)
        mng.simulate_scene(verbose=burg_params.view_simulation)
        mng.check_status()
        mng.lock_transform(burg_params.lock_transform)
        utils.trigger_display_update(burg_params)
        bpy.context.window.cursor_set("DEFAULT")
        return {'FINISHED'}


class BURG_OT_empty_scene(bpy.types.Operator):
    """ Creates an empty scene """

    bl_idname = "burg.empty_scene"
    bl_label = "Create Empty Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.context.window.cursor_set("WAIT")
        burg_params = context.scene.burg_params
        mng.synchronize()
        mng.remove_blender_objects()
        mng.empty_scene(burg_params.object_library_file,
                        ground_area=utils.get_size(
                            burg_params.area_size))
        mng.simulate_scene(verbose=burg_params.view_simulation)
        mng.check_status()
        utils.trigger_display_update(burg_params)
        bpy.context.window.cursor_set("DEFAULT")
        return {'FINISHED'}


class BURG_OT_update_scene(bpy.types.Operator):
    """ Update scene """

    bl_idname = "burg.update_scene"
    bl_label = "Update"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(self, context):
        return (context is not None and mng.is_valid_scene())

    def execute(self, context):
        bpy.context.window.cursor_set("WAIT")
        mng.synchronize()
        mng.update_scene_poses()
        burg_params = bpy.context.scene.burg_params
        if(mng.check_status()):
            mng.simulate_scene(verbose=burg_params.view_simulation)
            mng.update_blender_poses()
            mng.check_status()

        utils.trigger_display_update(burg_params)
        bpy.context.window.cursor_set("DEFAULT")
        return{'FINISHED'}


class BURG_OT_load_object_library(bpy.types.Operator):
    """ Loading object library information """

    bl_idname = "burg.load_object_library"
    bl_label = "Load Object Library"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="*.yaml")
    filter_glob: bpy.props.StringProperty(default="*.yaml", options={'HIDDEN'})

    def execute(self, context):
        try:
            bpy.context.window.cursor_set("WAIT")
            # Try to load the library and check if complete
            object_library = burg.ObjectLibrary.from_yaml(self.filepath)
            if object_library and object_library.objects_have_all_attributes():
                burg_params = context.scene.burg_params
                mng.remove_blender_objects()
                mng.empty_scene(self.filepath,
                                ground_area=utils.get_size(burg_params.area_size))
                burg_params.object_library_file = self.filepath
                update_previews(self, context)
                utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
                bpy.context.window.cursor_set("DEFAULT")
            elif object_library and not object_library.objects_have_all_attributes():
                # parameterize and call confirmation dialog
                bpy.ops.burg.library_completion_confirm('INVOKE_DEFAULT', filepath = self.filepath, currentpath=self.filepath)
            else:
                self.report({'ERROR'}, f"Could not open object library: {self.filepath}")
                bpy.context.window.cursor_set("DEFAULT")
                return {'CANCELLED'}
            return {'FINISHED'}
        except Exception as e:
            tb = traceback.format_exc()
            text = str(
                f"Could not open burg object library: {self.filepath}\n{e}\n{tb}")
            print(text)
            self.report({'ERROR'}, text)
            bpy.context.window.cursor_set("DEFAULT")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}




class BURG_OT_library_completion_confirm(bpy.types.Operator):
    """Confirm Object Library Completion"""
    bl_idname = "burg.library_completion_confirm"
    bl_label = "Complete Object Library"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
   
    scenepath: bpy.props.StringProperty(subtype="FILE_PATH", default="", options={'HIDDEN'})
    currentpath: bpy.props.StringProperty(subtype="FILE_PATH", default="object_library.yaml", options={'HIDDEN'})
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="object_library.yaml", options={'HIDDEN'})
    save_to: bpy.props.EnumProperty(name="Save to", description="Save completed library using current or new file.",
                                 items={
                                 ("A_New_File", "New File", "Save as new file", 0),
                                 ("B_Current_File", "Current File", "Overwrite current file", 1)},
                                 default=0)
                            
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if self.save_to == "A_New_File":
            bpy.ops.burg.library_completion('INVOKE_DEFAULT', 
                                            scenepath=self.scenepath, 
                                            filepath=self.filepath, 
                                            currentpath=self.currentpath)
        else:
            bpy.ops.burg.library_completion(scenepath=self.scenepath, 
                                            filepath=self.filepath, 
                                            currentpath=self.currentpath)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="The chosen object library is incomplete.")
        row = layout.row()
        row.label(text="You can complete it now by saving to:")
        row = layout.row()
        row.prop(self,"save_to", text="", expand=False)
        row = layout.row()
        row.label(text="Please be patient, as completion can take some time.")
        row = layout.row()
        row.label(text="Confirm your choice or cancel by hitting 'Esc'.")


class BURG_OT_library_completion(bpy.types.Operator):
    """Complete Object Library"""
    bl_idname = "burg.library_completion"
    bl_label = "Complete Object Library"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    scenepath: bpy.props.StringProperty(subtype="FILE_PATH")
    currentpath: bpy.props.StringProperty(subtype="FILE_PATH")
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.yaml")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            bpy.context.window.cursor_set("WAIT")
            if self.scenepath:
                burg_params = context.scene.burg_params
                mng.load_scene(scene_file=self.scenepath, savepath=self.filepath)
                burg_params.object_library_file = self.filepath
                update_previews(self, context)
                utils.update_display_colors()
                mng.lock_transform(burg_params.lock_transform)
                burg_params.area_size = utils.BURG_TO_BLENDER_SIZES[mng.scene.ground_area]
                utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
                bpy.context.window.cursor_set("DEFAULT")
            else:
                burg_params = context.scene.burg_params
                mng.remove_blender_objects()
                mng.empty_scene(self.currentpath,
                                ground_area=utils.get_size(burg_params.area_size),
                                savepath=self.filepath)
                burg_params.object_library_file = self.filepath
                update_previews(self, context)
                utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
            bpy.context.window.cursor_set("DEFAULT")
            return {'FINISHED'}
        except Exception as e:
            tb = traceback.format_exc()
            text = str(
                f"Could not load file: {self.filepath}:\n{e}\n{tb}")
            print(text)
            self.report({'ERROR'}, text)
            bpy.context.window.cursor_set("DEFAULT")
        return {'CANCELLED'}

    def invoke(self, context, event):
       # asks the user where to save object library
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BURG_OT_save_printout(bpy.types.Operator):
    """ Saving setup printout to file """

    bl_idname = "burg.save_printout"
    bl_label = "Save Printout"
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH", default="printout.pdf")

    @classmethod
    def poll(self, context):
        return (context is not None and mng.is_valid_scene())

    def execute(self, context):
        try:
            bpy.context.window.cursor_set("WAIT")
            # check and simulate current scene
            mng.synchronize()
            mng.update_scene_poses()
            burg_params = context.scene.burg_params
            invalid = False
            if(mng.check_status()):
                mng.simulate_scene(verbose=False)
                mng.update_blender_poses()
                if(mng.check_status()):
                    print_size = utils.get_size(burg_params.printout_size)
                    printout = burg.printout.Printout(
                        size=mng.scene.ground_area)
                    printout.add_scene(mng.scene)
                    printout.save_pdf(self.filepath, page_size=print_size,
                                      margin_mm=burg_params.printout_margin)
                else:
                    invalid = True
            else:
                invalid = True

            if invalid:
                # status of object not clear cannot save printout
                text = f"Could not safe printout. Some objects are obstructed or out of bounds."
                self.report({'WARNING'}, text)

            utils.trigger_display_update(burg_params)
            bpy.context.window.cursor_set("DEFAULT")
            return {'FINISHED'}
        except Exception as e:
            tb = traceback.format_exc()
            text = f"Could not save template file: {self.filepath}\n{e}\n{tb}"
            print(text)
            self.report({'ERROR'}, text)
            bpy.context.window.cursor_set("DEFAULT")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BURG_OT_save_scene(bpy.types.Operator):
    """ Saving scene setup to file """

    bl_idname = "burg.save_scene"
    bl_label = "Save Scene"
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH", default="scene.yaml")

    @classmethod
    def poll(self, context):
        return (context is not None and mng.is_valid_scene())

    def execute(self, context):
        try:
            bpy.context.window.cursor_set("WAIT")
            # check and simulate current scene
            mng.synchronize()
            mng.update_scene_poses()
            if(mng.check_status()):
                mng.simulate_scene(verbose=False)
                mng.update_blender_poses()
                mng.check_status()

            burg_params = context.scene.burg_params
            utils.trigger_display_update(burg_params)

            # printout parameter necessary?
            mng.save_scene(self.filepath)
            bpy.context.window.cursor_set("DEFAULT")
            return {'FINISHED'}
        except Exception as e:
            tb = traceback.format_exc()
            text = str(
                f"Could not save scene file: {self.filepath}:\n{e}\n{tb}")
            print(text)
            self.report({'ERROR'}, text)
            bpy.context.window.cursor_set("DEFAULT")
            return {'CANCELLED'}

    def invoke(self, context, event):
       # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}



class BURG_OT_load_scene(bpy.types.Operator):
    """ Loading scene setup from file """

    bl_idname = "burg.load_scene"
    bl_label = "Load Scene"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="*.yaml")
    filter_glob: bpy.props.StringProperty(default="*.yaml")

    def execute(self, context):
        try:
            bpy.context.window.cursor_set("WAIT")
            # We have to load the scene and check if the object library is complete
            scene, object_library, _ = burg.Scene.from_yaml(self.filepath)
            if object_library and object_library.objects_have_all_attributes():
                mng.load_scene(self.filepath)
                burg_params = context.scene.burg_params
                burg_params.object_library_file = mng.object_library_file
                update_previews(self, context)
                utils.update_display_colors()
                mng.lock_transform(burg_params.lock_transform)
                burg_params.area_size = utils.BURG_TO_BLENDER_SIZES[mng.scene.ground_area]
                utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
                bpy.context.window.cursor_set("DEFAULT")
            elif object_library and not object_library.objects_have_all_attributes():
                # parameterize and call confirmation dialog
                bpy.ops.burg.library_completion_confirm('INVOKE_DEFAULT', 
                                                        filepath = object_library.filename, 
                                                        currentpath = object_library.filename,
                                                        scenepath = self.filepath)
            else:
                self.report({'ERROR'}, f"Could not open object library: {self.filepath}")
                bpy.context.window.cursor_set("DEFAULT")
                return {'CANCELLED'}
            return {'FINISHED'}
        except Exception as e:
            tb = traceback.format_exc()
            text = str(
                f"Could not load scene file: {self.filepath}\n{e}\n{tb}")
            print(text)
            self.report({'ERROR'}, text)
            bpy.context.window.cursor_set("DEFAULT")
            return {'CANCELLED'}

    def invoke(self, context, event):
       # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# SCENE PANELS
class BURG_PT_get_started(bpy.types.Panel):
    bl_label = "Get Started..."
    bl_idname = "BURG_PT_get_started"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None)

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        flow = layout.grid_flow(row_major=True,
                                columns=0,
                                even_columns=True,
                                even_rows=False,
                                align=True)

        burg_params = scene.burg_params
        row = layout.row()
        row.operator("burg.load_object_library", text='Load Object Library')
        row = layout.row()
        row.operator("burg.load_scene", text="Load Scene")
        row = layout.row()
        row.enabled = False
        row.prop(burg_params, "object_library_file")


class BURG_PT_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "BURG_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_object_library())

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        burg_params = scene.burg_params

        row = layout.row()
        row.prop(burg_params, "view_mode", text="Display", expand=True)
        row = layout.row()
        row.prop(burg_params, "lock_transform", text="Restrict Movement")
        row = layout.row()
        row.prop(burg_params, "view_simulation", text="Show Simulation")


class BURG_PT_scene(bpy.types.Panel):
    bl_label = "Scene"
    bl_idname = "BURG_PT_scene"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_object_library())

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        burg_params = scene.burg_params

        row = layout.row()
        row.prop(burg_params, "area_size", text='Size')
        row = layout.row()
        row.operator("burg.empty_scene", text="Clear Scene")
        row = layout.row()
        row.operator("burg.save_scene", text="Save Scene")
        row = layout.row()
        row.operator("burg.save_printout", text='Save Printout')
        row = layout.row()
        row.prop(burg_params, "printout_size", text='Page Size')
        row = layout.row()
        row.prop(burg_params, "printout_margin", text='Margin (mm)')
        row = layout.row()
        row.operator("burg.update_scene", text="Validate & Simulate")


class BURG_PT_object_selection(bpy.types.Panel):
    """Selection panel for objects"""

    bl_label = "Object Placement"
    bl_idname = "BURG_PT_object_selection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_object_library())

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        obj = context.active_object
        scene = context.scene
        burg_params = context.scene.burg_params
        row = layout.row()
        row.operator("burg.random_scene", text='Random Configuration')
        row = layout.row()
        row.prop(burg_params, "number_objects", text='#Objects')
        row = layout.row()
        row.prop(burg_params, "number_instances", text='#Instances')
        row = layout.row()
        row.label(text="Object Selector")
        row = layout.row()
        row.template_list("BURG_UL_objects", "", scene,
                          "burg_objects", scene, "burg_object_index", rows=5)
        row = layout.row()
        row.operator("burg.add_object", text="Add Object")

        if obj and mng.has_stable_poses(obj) and obj.select_get():
            row = layout.row()
            row.prop(context.active_object,
                     "burg_stable_poses", text="Stable Poses")


class BURG_PT_object_preview(bpy.types.Panel):
    """Preview panel for selected object"""

    bl_label = "Preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = "BURG_PT_object_preview"
    bl_parent_id = "BURG_PT_object_selection"
    bl_category = "BURG Setup Template"

    def draw(self, context):
        global burg_object_previews

        layout = self.layout
        scene = context.scene
        if scene.burg_objects and scene.burg_object_index >= 0 and burg_object_previews:
            key = scene.burg_objects[scene.burg_object_index]
            layout.template_icon(burg_object_previews[key.id].icon_id, scale=7)


# OBJECT BROWSER OPERATORS
class BURG_OT_add_object(bpy.types.Operator):
    """
    Adds new object to scene
    """

    bl_idname = "burg.add_object"
    bl_label = "Add object"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(self, context):
        return (context is not None and mng.is_valid_scene())

    def execute(self, context):
        scene = context.scene
        burg_params = context.scene.burg_params
        if scene.burg_objects and scene.burg_object_index >= 0:
            key = scene.burg_objects[scene.burg_object_index]
            obj = mng.add_object(key.id)
            utils.set_active_and_select(obj)
            bpy.ops.burg.update_scene()
            mng.lock_transform(burg_params.lock_transform)
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# OBJECT BROWSER PANELS
burg_object_previews = None


class BURG_UL_objects(bpy.types.UIList):
    """
    List of available objects
    """

    first_run: bpy.props.BoolProperty(name="first_run", default=True)

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        global burg_object_previews

        if self.first_run:
            self.use_filter_show = True
            self.use_filter_sort_alpha = True
            self.first_run = False

        if item and burg_object_previews:
            layout.label(text=item.name,
                         icon_value=burg_object_previews[item.id].icon_id)


# OBJECT BROWSER PROPERTIES
def update_burg_object_index(self, context):
    scene = context.scene
    if scene.burg_object_index >= 0 and scene.burg_object_list:
        item = scene.burg_object_list[scene.burg_object_index]


def update_previews(self, context):
    global burg_object_previews

    scene = context.scene
    try:
        mng = utils.SceneManager()
        bol = mng.object_library
        if not mng.is_valid_object_library():
            return

        if burg_object_previews:
            bpy.utils.previews.remove(burg_object_previews)
            burg_object_previews = None

        scene.burg_objects.clear()

        burg_object_previews = bpy.utils.previews.new()

        for o in mng.object_library:
            item = scene.burg_objects.add()
            item.id = o
            item.name = bol[o].name
            # add the preview to the collection
            thumb_file = bol[o].thumbnail_fn
            if thumb_file and os.path.isfile(thumb_file):
                burg_object_previews.load(
                    item.id, bol[o].thumbnail_fn, 'IMAGE')
            else:
                resources_folder = utils.get_resources_folder()
                burg_object_previews.load(
                    item.id, os.path.join(resources_folder, 'missing_image.png'), 'IMAGE')
    except Exception as e:
        print(f"An error occurred creating previews.")
        print(e)


def update_stable_poses(self, context):
    mng.set_to_stable_pose(context.active_object)


def set_stable_poses(self, value):
    active = bpy.context.active_object
    if active and mng.is_burg_object(active):
        n = len(mng.get_stable_poses(active))
        self["burg_stable_poses"] = (value) % n

    for area in bpy.context.screen.areas:
        area.tag_redraw()


def get_stable_poses(self):
    return self.get("burg_stable_poses", 0)


class BURG_PG_object(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(name="Id")
    name: bpy.props.StringProperty(name="Name")


# SCENE PROPERTIES

def update_lock_transform(self, context):
    burg_params = context.scene.burg_params
    mng.lock_transform(burg_params.lock_transform)


def update_area_size(self, context):
    bpy.context.window.cursor_set("WAIT")
    burg_params = context.scene.burg_params
    plane = bpy.context.scene.objects["Plane"]
    size = utils.get_size(burg_params.area_size)
    plane.dimensions = [size[0], size[1], 0]
    plane.location = [size[0]/2, size[1]/2, 0]
    material = plane.active_material
    img = bpy.data.images["layout_empty_printout.png"]
    np_image = burg.printout.Printout(size).get_image()
    h, w = np_image.shape
    img.scale(w, h)

    img.pixels[:] = utils.convert_numpy_image(np_image)
    img.update()

    if mng.is_valid_scene():
        mng.set_area_size(burg_params.area_size)
        if mng.check_status():
            mng.simulate_scene(verbose=burg_params.view_simulation)
            mng.check_status()

    utils.trigger_display_update(burg_params)
    bpy.context.window.cursor_set("DEFAULT")


def update_display_colors(self, context):
    utils.update_display_colors()


class BURG_PG_params(bpy.types.PropertyGroup):
    number_objects: bpy.props.IntProperty(
        name="#Objects used for Random Scene.", default=1, min=1)
    number_instances: bpy.props.IntProperty(
        name="#Instances used for Random Scene.", default=1, min=1)
    view_simulation: bpy.props.BoolProperty(
        name="View Simulation", default=False,
        description="Enables viewing realtime simulation. Do not "
        "close the window, instead wait until the simulation has finished")
    object_library_file: bpy.props.StringProperty(
        name="Object Library", default="")
    lock_transform: bpy.props.BoolProperty(
        name="Lock Transform", default=True, update=update_lock_transform)
    view_mode: bpy.props.EnumProperty(
        items=[('view_color', 'Color', 'Object Color', '', 0),
               ('view_state', 'State', 'Object State', '', 1)],
        default=1, update=update_display_colors)
    printout_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Printout Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Printout Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Printout Size A4', '', 2)],
        default=0)
    area_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Area Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Area Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Area Size A4', '', 2)],
        default=0,
        update=update_area_size)
    printout_margin: bpy.props.FloatProperty(
        name="Printout Margin", default=0.0, min=0.0)


# GENERAL OPERATORS
class delete_override(bpy.types.Operator):
    # Overriding delete operator
    # From: https://blender.stackexchange.com/questions/135122/how-to-prepend-to-delete-operator
    """delete objects and their derivatives"""

    bl_idname = "object.delete"
    bl_label = "Object Delete Operator"
    bl_options = {"REGISTER", "UNDO"}
    use_global: bpy.props.BoolProperty()
    confirm: bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        mng = utils.SceneManager()
        for obj in context.selected_objects:
            if mng.is_burg_object(obj):
                mng.remove_object(obj)
            else:
                bpy.data.objects.remove(obj)

        return {'FINISHED'}

    def invoke(self, context, event):
        if event.type == 'X':
            return context.window_manager.invoke_confirm(self, event)
        else:
            return self.execute(context)


class delete_outliner_override(bpy.types.Operator):
    # Overriding delete operator
    # From: https://blender.stackexchange.com/questions/135122/how-to-prepend-to-delete-operator
    """delete objects and their derivatives"""

    bl_idname = "outliner.delete"
    bl_label = "Object Delete Operator"
    bl_options = {"REGISTER", "UNDO"}
    use_global: bpy.props.BoolProperty()
    confirm: bpy.props.BoolProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        mng = utils.SceneManager()
        for obj in context.selected_objects:
            if mng.is_burg_object(obj):
                mng.remove_object(obj)
            else:
                bpy.data.objects.remove(obj)

        return {'FINISHED'}

    def invoke(self, context, event):
        if event.type == 'X':
            return context.window_manager.invoke_confirm(self, event)
        else:
            return self.execute(context)


@persistent
def load_handler(scene):
    # Blender does not allow to store persistent data over several blend files.
    # Thus removing current scene and starting from scratch is the only way
    sync_handler(scene)
    mng.update_scene_poses()
    mng.check_status()
    utils.update_display_colors()


@persistent
def sync_handler(scene):
    global burg_object_previews

   # check if the object_library file has changed
    if not bpy.context.scene or not bpy.context.scene.get("burg_params"):
       # starting fresh
        if mng.is_valid_scene():
            mng.scene.objects.clear()
            mng.scene = None
            mng.object_library = None
            mng.object_library_file = None
            mng.blender_to_burg.clear()
            if burg_object_previews:
                bpy.utils.previews.remove(burg_object_previews)
                burg_object_previews = None
            if bpy.context.scene.burg_objects:
                burg_objects.clear()
        return

    current_library_file = bpy.context.scene.burg_params.object_library_file
    mng_library_file = None
    if mng.object_library:
        mng_library_file = mng.object_library.filename

    #TODO: Important note on UNDO operation:
    #      Switching between library files with same name which are
    #      Incomplete / Complete does not reload the library
    #      Also it is unclear what should be the real state since you cannot
    #      UNDO a completed library
    if not (current_library_file == mng_library_file):
        # check if we still have a scene
        if not mng.is_valid_scene() and current_library_file:
            # need to create a valid scene with the proposed object library
            bpy.ops.burg.load_object_library(filepath=current_library_file)
        elif mng.is_valid_scene() and current_library_file:
            bpy.ops.burg.load_object_library(filepath=current_library_file)
        elif mng.is_valid_scene() and not current_library_file:
            mng.scene.objects.clear()
            mng.scene = None
            mng.object_library = None
            mng.object_library_file = None
            if burg_object_previews:
                bpy.utils.previews.remove(burg_object_previews)
                burg_object_previews = None
            if bpy.context.scene.burg_objects:
                burg_objects.clear()
        else:
            for area in bpy.context.screen.areas:
                area.tag_redraw()

    mng.synchronize()


classes = (
    BURG_PT_get_started,
    BURG_PT_scene,
    BURG_PT_object_selection,
    BURG_PT_object_preview,
    BURG_PT_settings,

    BURG_OT_update_scene,
    BURG_OT_empty_scene,
    BURG_OT_save_scene,
    BURG_OT_load_scene,
    BURG_OT_random_scene,
    BURG_OT_load_object_library,
    BURG_OT_save_printout,

    BURG_PG_params,
    BURG_OT_add_object,
    BURG_UL_objects,
    BURG_PG_object,
    # delete_override,
    # delete_outliner_override,
    BURG_OT_library_completion,
    BURG_OT_library_completion_confirm,
)

# KEYMAPS
addon_keymaps = []


def add_keymap():
    global addon_keymaps
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon

    if kc:
        km = wm.keyconfigs.addon.keymaps.new(
            name='3D View', space_type='VIEW_3D')

        kmi = km.keymap_items.new(
            BURG_OT_save_scene.bl_idname, 'S', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new(
            BURG_OT_save_printout.bl_idname, 'P', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))

        kmi = km.keymap_items.new(
            BURG_OT_update_scene.bl_idname, 'V', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.burg_params = bpy.props.PointerProperty(
        type=BURG_PG_params)

    bpy.types.Scene.burg_objects = bpy.props.CollectionProperty(
        name="BURG Objects",
        type=BURG_PG_object,
    )

    bpy.types.Scene.burg_object_index = bpy.props.IntProperty(
        name="Index for Object List")

    bpy.types.Object.burg_stable_poses = bpy.props.IntProperty(name="Stable Poses",
                                                               set=set_stable_poses,
                                                               get=get_stable_poses,
                                                               update=update_stable_poses
                                                               )

    bpy.app.handlers.undo_post.append(sync_handler)
    bpy.app.handlers.redo_post.append(sync_handler)
    bpy.app.handlers.load_post.append(load_handler)

    add_keymap()


def unregister():
    global burg_object_previews

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in classes:
        bpy.utils.unregister_class(cls)

    if burg_object_previews:
        bpy.utils.previews.remove(burg_object_previews)
        burg_object_previews = None

    del bpy.types.Scene.burg_params
    del bpy.types.Scene.burg_objects
    del bpy.types.Scene.burg_object_index
    del bpy.types.Object.burg_stable_poses

    bpy.app.handlers.undo_post.remove(sync_handler)
    bpy.app.handlers.redo_post.remove(sync_handler)
    bpy.app.handlers.load_post.remove(load_handler)


if __name__ == "__main__":
    register()
