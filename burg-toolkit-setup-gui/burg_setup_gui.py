import bpy.utils.previews
import bpy
import mathutils

import burg_toolkit as burg
import burg_setup_gui_utils as utils

import os
import numpy as np

# the one and only manager
mng = utils.SceneManager()


# SCENE OPERATORS
class BURG_OT_random_scene(bpy.types.Operator):
    """ Creates a random scene """

    bl_idname = "burg.random_scene"
    bl_label = "Create Random Scene"

    def execute(self, context):
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
        return {'FINISHED'}


class BURG_OT_empty_scene(bpy.types.Operator):
    """ Creates an empty scene """

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
    """ Update scene """

    bl_idname = "burg.update_scene"
    bl_label = "Update Scene"

    def execute(self, context):
        print("Update scene")
        mng.synchronize()
        mng.update_scene_poses()
        burg_params = bpy.context.scene.burg_params
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

    def execute(self, context):
        try:
            # TODO: Error handling when opening incomplete/not processed library file.
            burg_params = context.scene.burg_params
            burg_params.object_library_file = self.filepath
            mng.empty_scene(burg_params.object_library_file, 
                            ground_area = utils.get_size(burg_params.area_size))
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
    """ Saving setup printout to file """

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
            printout = burg.printout.Printout(size=mng.scene.ground_area)
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


class BURG_OT_save_scene(bpy.types.Operator):
    """ Saving scene setup to file """

    bl_idname = "burg.save_scene"
    bl_label = "Save Scene"
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH", default="scene.yaml")

    @classmethod
    def poll(cls, context):
        return mng.scene is not None

    def execute(self, context):
        try:
            # printout parameter necessary?
            mng.save_scene(self.filepath)
            return {'FINISHED'}
        except Exception as e:
            print(f"Could not save scene file: {self.filepath}.")
            print(e)
            return {'CANCELLED'}

    def invoke(self, context, event):
       # if not mng.scene:
       #     return

       # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BURG_OT_load_scene(bpy.types.Operator):
    """ Loading scene setup from file """

    bl_idname = "burg.load_scene"
    bl_label = "Load Scene"
    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH", default="*.yaml")

    def execute(self, context):
        try:
            mng.load_scene(self.filepath)
            # TODO: Error handling when opening incomplete/not processed library file.
            burg_params = context.scene.burg_params
            burg_params.object_library_file = mng.object_library_file
            update_burg_objects(self, context)
            utils.update_display_colors()
            mng.lock_transform(burg_params.lock_transform)
            
            burg_params.area_size = utils.BURG_TO_BLENDER_SIZES[mng.scene.ground_area] 

            utils.tag_redraw(context, space_type='VIEW_3D', region_type='UI')
            return {'FINISHED'}
        except Exception as e:
            print(f"Could not load scene file: {self.filepath}.")
            print(e)
            return {'CANCELLED'}

    def invoke(self, context, event):
       # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# SCENE PANELS
class BURG_PT_object_library(bpy.types.Panel):
    bl_label = "Scene"
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
        row.operator("burg.load_object_library", text='New')
        row = layout.row()
        row.operator("burg.load_scene", text="Open")
        row = layout.row()
        row.operator("burg.save_scene", text="Save")
        row = layout.row()
        row.prop(burg_params, "area_size", text="Size")
        row = layout.row()
        row.enabled = False
        row.prop(burg_params, "object_library_file")


class BURG_PT_scene(bpy.types.Panel):
    bl_label = "Scene Actions"
    bl_idname = "BURG_PT_scene"
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
        row.operator("burg.update_scene")
        row = layout.row()
        row.prop(burg_params, "view_mode", text="Display", expand=True)
        row = layout.row()
        row.prop(burg_params, "lock_transform", text="Lock Move")
        row = layout.row()
        row.prop(burg_params, "view_simulation")

        if obj and mng.has_stable_poses(obj):
            row = layout.row()
            row.prop(context.active_object,
                     "burg_stable_poses", text="Stable Poses")


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
        return (context is not None and mng.is_valid_scene())

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
    """
    Adds new object to scene
    """

    bl_idname = "burg.add_object"
    bl_label = "Add object"

    def execute(self, context):
        print("Add object")
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


def get_preview(key):
    global burg_object_previews

    if burg_object_previews:
        if key not in burg_object_previews:
            print(f"Preview key {key} not found")
            #TODO: preview_key = "missing_preview"
            return None
        else:
            return burg_object_previews[key]
    else:
        return None


class BURG_UL_objects(bpy.types.UIList):
    """
    List of available objects
    """

    global burg_object_previews

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item and burg_object_previews:
            layout.label(text=item.name,
                         icon_value=burg_object_previews[item.id].icon_id)


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
        scene = context.scene
        row = layout.row()
        row.template_list("BURG_UL_objects", "", scene,
                          "burg_objects", scene, "burg_object_index", rows=5)
        row = layout.row()
        row.operator("burg.add_object")


class BURG_PT_object_preview(bpy.types.Panel):
    """Preview panel for selected object"""
    global burg_object_previews

    bl_label = "Preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_idname = "BURG_PT_object_preview"
    bl_parent_id = "BURG_PT_object_selection"
    bl_category = "BURG Setup Template"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.burg_objects and scene.burg_object_index >= 0 and burg_object_previews:
            key = scene.burg_objects[scene.burg_object_index]
            layout.template_icon(burg_object_previews[key.id].icon_id, scale=7)


# OBJECT BROWSER PROPERTIES
class BURG_PG_object(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(name="Id")
    name: bpy.props.StringProperty(name="Name")


def update_burg_object_index(self, context):
    print("update_burg_object_index")
    global burg_object_previews

    scene = context.scene

    if not burg_object_previews:
        print("previews are empty")
        return

    if not scene.burg_object_index:
        print("previews are empty")
        return

    if not scene.burg_object_list.get(scene.burg_object_index):
        print("index is not found")

    if scene.burg_object_index >= 0 and scene.burg_object_list:
        try:
            item = scene.burg_object_list[scene.burg_object_index]
        except Exception as e:
            print("Preview error:")
            print(e)


def update_burg_objects(self, context):
    print("update_burg_objects")
    global burg_object_previews

    scene = context.scene
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
    print("update_stable_poses")
    mng.set_to_stable_pose(context.active_object)


def set_stable_poses(self, value):
    print("set_stable_poses")
    active = bpy.context.active_object
    if active and mng.is_burg_object(active):
        n = len(mng.get_stable_poses(active))
        self["burg_stable_poses"] = (value) % n

    for area in bpy.context.screen.areas:
        area.tag_redraw()


def get_stable_poses(self):
    return self.get("burg_stable_poses", 0)

# SCENE PROPERTIES


def update_lock_transform(self, context):
    print("update_lock_transform")
    burg_params = context.scene.burg_params
    mng.lock_transform(burg_params.lock_transform)


def update_area_size(self, context):
    print("update_area_size")
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

def update_display_colors(self, context):
    print("update_display_colors")
    utils.update_display_colors()
    print("finished")
    
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
    print("Called delete overrid")
    # Overriding delete operator
    # From: https://blender.stackexchange.com/questions/135122/how-to-prepend-to-delete-operator
    """delete objects and their derivatives"""

    bl_idname = "object.delete"
    bl_label = "Object Delete Operator"
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

from bpy.app.handlers import persistent


@persistent
def sync_handler(scene):
    global burg_object_previews
    print("Called Sync Handler")
    #check if the object_library file has changed
    current_library_file = scene.burg_params.object_library_file
    mng_library_file = None
    print(f"current {current_library_file}")
    if mng.object_library:
        print(f"scene {mng.object_library.filename}")
        mng_library_file = mng.object_library.filename

    if not (current_library_file == mng_library_file):
        print("Object library has changed")
       #check if we still have a scene
        if not mng.is_valid_scene() and current_library_file:
            print("Current Scene is invalid and new library file")
            # need to create a valid scene with the proposed object library
            bpy.ops.burg.load_object_library(filepath = current_library_file)
        elif mng.is_valid_scene() and current_library_file:
            print("Current Scene is valid and new library file")
            bpy.ops.burg.load_object_library(filepath = current_library_file)
        elif mng.is_valid_scene() and not current_library_file:
            print("Current Scene is valid and new library file is invalid")
            mng.scene = None
            mng.object_library = None
            mng.object_library_file = None
            print("Clear the previews")
            if burg_object_previews:
                bpy.utils.previews.remove(burg_object_previews)
        else:
            # not mng.is_valid_scene() and not current_library_file
            print("No valid scene and no new library file")
            print(f"{mng.is_valid_scene()}")
            print(f"{current_library_file}")
            for area in bpy.context.screen.areas:
                area.tag_redraw()
            return

    mng.synchronize()

    for area in bpy.context.screen.areas:
        area.tag_redraw()

classes = (
    BURG_PT_object_library,
    BURG_PT_new_scene,
    BURG_PT_scene,

    BURG_OT_update_scene,
    BURG_OT_empty_scene,
    BURG_OT_save_scene,
    BURG_OT_load_scene,
    BURG_OT_random_scene,
    BURG_OT_load_object_library,
    BURG_OT_save_printout,

    BURG_PG_params,

    BURG_PT_object_selection,
    BURG_PT_object_preview,

    BURG_PT_printout,

    BURG_OT_add_object,

    BURG_UL_objects,

    BURG_PG_object,

    delete_override,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.burg_params = bpy.props.PointerProperty(
        type=BURG_PG_params)

    bpy.types.Scene.burg_objects = bpy.props.CollectionProperty(
        name="BURG Objects",
        type=BURG_PG_object
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


def unregister():
    global burg_object_previews

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

if __name__ == "__main__":
    register()
