import bpy.utils.previews
import bpy
import burg_toolkit as burg
import burg_setup_gui_utils as utils

import os
import numpy as np
from PIL import Image

# the one and only manager
mng = utils.SceneManager()


# SCENE OPERATORS
class BURG_OT_random_scene(bpy.types.Operator):
    bl_idname = "burg.random_scene"
    bl_label = "Create Random Scene"

    def execute(self, context):
        burg_params = context.scene.burg_params
        mng.random_scene(burg_params.object_library_file,
                         n_instances=burg_params.number_objects,
                         ground_area=utils.get_size(
                             burg_params.area_size),
                         n_instances_objects=burg_params.number_instances)
        mng.simulate_scene(verbose=burg_params.view_simulation)
        mng.remove_blender_objects()
        mng.load_objects()
        mng.check_status()
        mng.lock_transform(burg_params.lock_transform)
        utils.trigger_display_update(burg_params)
        return {'FINISHED'}


class BURG_OT_empty_scene(bpy.types.Operator):
    bl_idname = "burg.empty_scene"
    bl_label = "Create Empty Scene"

    def execute(self, context):
        burg_params = context.scene.burg_params
        mng.empty_scene(burg_params.object_library_file,
                        ground_area=utils.get_size(
                            burg_params.area_size))
        mng.simulate_scene(verbose=burg_params.view_simulation)
        mng.remove_blender_objects()
        mng.check_status()
        utils.trigger_display_update(burg_params)
        return {'FINISHED'}


class BURG_OT_update_scene(bpy.types.Operator):
    bl_idname = "burg.update_scene"
    bl_label = "Update Scene"

    def execute(self, context):
        mng.update_scene_poses()
        burg_params = bpy.context.scene.burg_params
        # mng.simulate_scene(verbose=True)
        if(mng.check_status()):
            mng.simulate_scene(verbose=burg_params.view_simulation)
            mng.update_blender_poses()
            mng.check_status()

        utils.trigger_display_update(burg_params)
        return{'FINISHED'}


class BURG_OT_load_object_library(bpy.types.Operator):
    """ Loading object library information """

    bl_idname = "burg.load_object_library"
    bl_label = "Load Object Library"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="*.yaml")
    loaded: bpy.props.BoolProperty(name="loaded", default=False)

    def execute(self, context):
        try:
            # TODO: Error handling when opening incomplete/not processed library file.
            burg_params = context.scene.burg_params
            burg_params.object_library_file = self.filepath
            mng.empty_scene(burg_params.object_library_file)
            update_burg_objects(self, context)
            utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
            return {'FINISHED'}
        except Exception as e:
            print(f"Could not open burg object library: {self.filepath}.")
            print(e)
            return {'CANCELLED'}

    def invoke(self, context, event):
        # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BURG_OT_save_printout(bpy.types.Operator):
    """ Saving setup printout to file. """

    bl_idname = "burg.save_printout"
    bl_label = "Save Printout"
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH", default="printout.pdf")

    def execute(self, context):
        try:
            if not mng.scene:
                return

            burg_params = context.scene.burg_params
            print_size = utils.get_size(burg_params.printout_size)
            printout = burg.Printout(size=mng.scene.ground_area)
            printout.add_scene(mng.scene)
            printout.save_pdf(self.filepath, page_size=print_size,
                              margin_mm=burg_params.printout_margin)
            return {'FINISHED'}
        except Exception as e:
            print(f"Could not save template file: {self.filepath}.")
            print(e)
            return {'CANCELLED'}

    def invoke(self, context, event):
        # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# SCENE PANELS
class BURG_PT_object_library(bpy.types.Panel):
    bl_label = "Object Library"
    bl_idname = "BURG_PT_object_library"
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
        row.enabled = False
        row.prop(burg_params, "object_library_file")
        row = layout.row()
        row.prop(burg_params, "area_size", text="Size")
        row = layout.row()
        row.operator("burg.load_object_library", text='Open')
        col = layout.column()
        col.separator()


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
        obj = context.object
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        burg_params = scene.burg_params

        row = layout.row()
        row.operator("burg.update_scene")
        row = layout.row()
        row.prop(burg_params, "view_mode", text="Display", expand=True)
        row = layout.row()
        row.prop(burg_params, "lock_transform", text="Lock Move")
        row = layout.row()
        row.prop(burg_params, "view_simulation")


class BURG_PT_new_scene(bpy.types.Panel):
    bl_label = "Create Scene"
    bl_idname = "BURG_PT_new_scene"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_object_library())

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        burg_params = scene.burg_params

        row = layout.row()
        row.operator("burg.empty_scene", text="Create Empty")
        row = layout.row()
        row.operator("burg.random_scene", text='Create Random')
        row = layout.row()
        row.prop(burg_params, "area_size", text='Size')
        row = layout.row()
        row.prop(burg_params, "number_objects", text='#Objects')
        row = layout.row()
        row.prop(burg_params, "number_instances", text='#Instances')


class BURG_PT_printout(bpy.types.Panel):
    bl_label = "Printout"
    bl_idname = "BURG_PT_printout"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_scene())

    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        burg_params = scene.burg_params

        row = layout.row()
        row.operator("burg.save_printout", text='Save')
        row = layout.row()
        row.prop(burg_params, "printout_size", text='Size')
        row = layout.row()
        row.prop(burg_params, "printout_margin", text='Margin (mm)')


# OBJECT BROWSER OPERATORS

class BURG_OT_add_object(bpy.types.Operator):
    bl_idname = "burg.add_object"
    bl_label = "Add object"

    def execute(self, context):
        wm = context.window_manager
        if wm.burg_objects and wm.burg_object_index >= 0:
            key = wm.burg_objects[wm.burg_object_index]
            mng = utils.SceneManager()
            mng.add_objects(key.id)
            bpy.ops.burg.update_scene()
            return {'FINISHED'}
        else:
            return {'CANCELLED'}


# OBJECT BROWSER PANELS
burg_object_previews = None


def get_preview(key):
    global burg_object_previews

    if burg_object_previews:
        if key not in burg_object_previews:
            print(f"Preview key {key} not found")
            #preview_key = "missing_preview"
            return None
        else:
            return burg_object_previews[key]
    else:
        return None


class BURG_UL_objects(bpy.types.UIList):
    global burg_object_previews

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item and burg_object_previews:
            layout.label(text=item.name,
                         icon_value=burg_object_previews[item.id].icon_id)

    def invoke(self, context, event):
        pass


class BURG_PT_object_selection(bpy.types.Panel):
    """Selection panel for objects"""
    bl_label = "Objects"
    bl_idname = "BURG_PT_object_selection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return (context is not None and utils.SceneManager().is_valid_object_library())


    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        row = layout.row()
        row.template_list("BURG_UL_objects", "", wm,
                          "burg_objects", wm, "burg_object_index", rows=5)
        row = layout.row()
        row.operator("burg.add_object")


class BURG_PT_object_preview(bpy.types.Panel):
    """PReview panel for selected object"""
    bl_label = "Preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = "BURG_PT_object_preview"
    bl_parent_id = "BURG_PT_object_selection"
    bl_category = "BURG Setup Template"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        if wm.burg_objects and wm.burg_object_index >= 0 and burg_object_previews:
            key = wm.burg_objects[wm.burg_object_index]
            layout.template_icon(burg_object_previews[key.id].icon_id, scale=7)


# OBJECT BROWSER PROPERTIES
class BURG_PG_object(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(name="Id")
    name: bpy.props.StringProperty(name="Name")


def update_burg_object_index(self, context):
    global burg_object_previews

    wm = context.window_manager

    if wm.burg_object_index >= 0 and wm.burg_object_list:
        item = wm.burg_object_list[wm.burg_object_index]


def update_burg_objects(self, context):
    global burg_object_previews
    global object_library

    wm = context.window_manager
    # Unfortunately this gets called everytime one clicks or opens the dialog
    # Even if canceling the dialog
    # Maybe make old and new entry compare and only reload when dirty

    try:
        mng = utils.SceneManager()
        bol = mng.object_library
        if not mng.is_valid_object_library():
            print("Object library is invalid.")
            return

        if burg_object_previews:
            bpy.utils.previews.remove(burg_object_previews)

        wm.burg_objects.clear()

        burg_object_previews = bpy.utils.previews.new()

        for o in mng.object_library:
            item = wm.burg_objects.add()
            item.id = o
            item.name = bol[o].name
            # add the preview to the collection
            thumb_file = bol[o].thumbnail_fn
            if thumb_file and os.path.isfile(thumb_file):
                burg_object_previews.load(
                    item.id, bol[o].thumbnail_fn, 'IMAGE')
            else:
                print(f"The thumbnail file {thumb_file} does not exist.")
    except Exception as e:
        print(
            f"An error occurred creating previews.")
        print(e)


# SCENE PROPERTIES
def update_lock_transform(self, context):
    mng = utils.SceneManager()
    burg_params = context.scene.burg_params
    mng.lock_transform(burg_params.lock_transform)


class BURG_PG_params(bpy.types.PropertyGroup):
    number_objects: bpy.props.IntProperty(
        name="#Objects used for Random Scene.", default=1)
    number_instances: bpy.props.IntProperty(
        name="#Instances used for Random Scene.", default=1)
    view_simulation: bpy.props.BoolProperty(
        name="View Simulation", default=False)
    object_library_file: bpy.props.StringProperty(
        name="Object Library", default="")
    lock_transform: bpy.props.BoolProperty(
        name="Lock Transform", default=False, update=update_lock_transform)
    view_mode: bpy.props.EnumProperty(
        items=[('view_color', 'Color', 'Object Color', '', 0),
               ('view_state', 'State', 'Object State', '', 1)],
        default=0, update=utils.update_display_colors)
    printout_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Printout Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Printout Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Printout Size A4', '', 2)],
        default=1)
    area_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Area Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Area Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Area Size A4', '', 2)],
        default=1)
    printout_margin: bpy.props.FloatProperty(
        name="Printout Margin", default=0.0, min=0.0)


classes = (
    BURG_PT_object_library,
    BURG_PT_new_scene,
    BURG_PT_scene,
    BURG_PT_printout,

    BURG_OT_update_scene,
    BURG_OT_empty_scene,
    BURG_OT_random_scene,
    BURG_OT_load_object_library,
    BURG_OT_save_printout,

    BURG_PG_params,

    BURG_PT_object_selection,
    BURG_PT_object_preview,

    BURG_OT_add_object,

    BURG_UL_objects,

    BURG_PG_object,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.burg_params = bpy.props.PointerProperty(
        type=BURG_PG_params)

    bpy.types.WindowManager.burg_objects = bpy.props.CollectionProperty(
        name="BURG Objects",
        type=BURG_PG_object
    )

    bpy.types.WindowManager.burg_object_index = bpy.props.IntProperty(
        name="Index for Object List")


def unregister():
    global burg_object_previews

    for cls in classes:
        bpy.utils.unregister_class(cls)

    if burg_object_previews:
        bpy.utils.previews.remove(burg_object_previews)

    del bpy.types.Scene.burg_params
    del bpy.types.WindowManager.burg_objects
    del bpy.types.WindowManager.burg_object_index


if __name__ == "__main__":
    register()
