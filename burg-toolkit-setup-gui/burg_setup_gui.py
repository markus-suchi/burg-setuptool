import bpy
import burg_toolkit as burg
import burg_setup_gui_utils as utils

import numpy as np
from PIL import Image

# the one and only manager
mng = utils.SceneManager()


class BURG_OT_random_scene(bpy.types.Operator):
    bl_idname = "burg.random_scene"
    bl_label = "Create Random Scene"

    def execute(self, context):
        burg_params = context.scene.burg_params
        print_size = utils.get_printout_size(burg_params.printout_size)
        mng.random_scene(burg_params.object_library_file,
                         n_instances=burg_params.number_objects,
                         ground_area=utils.get_printout_size(
                             burg_params.area_size),
                         n_instances_objects=burg_params.number_instances)
        mng.simulate_scene(verbose=burg_params.view_simulation)
        mng.remove_blender_objects()
        mng.load_objects()
        mng.check_status()
        utils.update_lock_transform(self, context)
        utils.trigger_display_update(burg_params)
        return {'FINISHED'}


class BURG_OT_update_scene(bpy.types.Operator):
    bl_idname = "burg.update_scene"
    bl_label = "Update Scene"

    def execute(self, context):
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
    loaded: bpy.props.BoolProperty(name="loaded", default=False)

    def execute(self, context):
        try:
            # TODO: Error handling when opening incomplete/not processed library file.
            burg_params = context.scene.burg_params
            burg_params.object_library_file = self.filepath
            mng.empty_scene(burg_params.object_library_file)
            return {'FINISHED'}
        except Exception:
            print(f"Could not open burg object library: {self.filepath}.")
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
            print_size = utils.get_printout_size(burg_params.printout_size)
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


class BURG_PT_setup_gui(bpy.types.Panel):
    bl_label = "BURG Setup Gui"
    bl_idname = "BURG_PT_setup_gui"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BURG Setup Template"

    @classmethod
    def poll(self, context):
        return context is not None

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
        # layout.label(text="Config:")
        row = layout.row()
        row.enabled = False
        row.prop(burg_params, "object_library_file")
        row = layout.row()
        row.prop(burg_params, "area_size")
        row = layout.row()
        row.operator("burg.load_object_library", text='Open')
        col = layout.column()
        col.separator()
        # layout.label(text="Creation:")
        row = layout.row()
        row.prop(burg_params, "number_objects")
        row = layout.row()
        row.prop(burg_params, "number_instances")
        row = layout.row()
        row.prop(burg_params, "view_simulation")
        row = layout.row()
        row.operator("burg.random_scene")
        # layout.label(text="Verification:")
        row = layout.row()
        row.operator("burg.update_scene")
        row = layout.row()
        row.prop(burg_params, "view_mode", text="Display", expand=True)
        row = layout.row()
        row.prop(burg_params, "lock_transform")
        layout.label(text="Printout:")
        row = layout.row()
        row.operator("burg.save_printout", text='Save')
        row.prop(burg_params, "printout_size", text='')
        row.prop(burg_params, "printout_margin", text='')


class BURG_PG_params(bpy.types.PropertyGroup):
    number_objects: bpy.props.IntProperty(name="#Objects", default=1)
    number_instances: bpy.props.IntProperty(name="#Instances", default=1)
    view_simulation: bpy.props.BoolProperty(
        name="View Simulation", default=False)
    object_library_file: bpy.props.StringProperty(
        name="Object Library", default="")
    lock_transform: bpy.props.BoolProperty(
        name="Lock Transform", default=False, update=utils.update_lock_transform)
    view_mode: bpy.props.EnumProperty(
        items=[('view_color', 'Color', 'Object Color', '', 0),
               ('view_state', 'State', 'Object State', '', 1)],
        default=0, update=utils.update_display_colors)
    printout_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Size A4', '', 2)],
        default=1)
    area_size: bpy.props.EnumProperty(
        items=[('SIZE_A2', 'A2', 'Size A2', '', 0),
               ('SIZE_A3', 'A3', 'Size A3', '', 1),
               ('SIZE_A4', 'A4', 'Size A4', '', 2)],
        default=1)
    printout_margin: bpy.props.FloatProperty(
        name="Printout Margin", default=0.0, min=0.0)


def register():
    bpy.utils.register_class(BURG_PT_setup_gui)
    bpy.utils.register_class(BURG_OT_random_scene)
    bpy.utils.register_class(BURG_OT_update_scene)
    bpy.utils.register_class(BURG_OT_load_object_library)
    bpy.utils.register_class(BURG_OT_save_printout)
    bpy.utils.register_class(BURG_PG_params)

    bpy.types.Scene.burg_params = bpy.props.PointerProperty(
        type=BURG_PG_params)


def unregister():
    bpy.utils.unregister_class(BURG_PT_setup_gui)
    bpy.utils.unregister_class(BURG_OT_random_scene)
    bpy.utils.unregister_class(BURG_OT_update_scene)
    bpy.utils.unregister_class(BURG_OT_load_object_library)
    bpy.utils.unregister_class(BURG_OT_save_printout)
    bpy.utils.unregister_class(BURG_PG_params)

    del bpy.types.Scene.burg_params


if __name__ == "__main__":
    register()
