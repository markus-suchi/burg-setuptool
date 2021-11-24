import bpy
import burg_toolkit as burg
import burg_setup_gui_utils as utils

object_library = None
scene = None


class BURG_OT_create_scene(bpy.types.Operator):
    bl_idname = "burg.create_scene"
    bl_label = "Create Random Scene"

    def execute(self, context):
        global object_library
        global scene

        if object_library:
            burg_params = context.scene.burg_params
            scene = utils.create_scene(
                object_library,  n_instances=burg_params.number_objects, n_instances_objects=burg_params.number_instances)
            utils.simulate_scene(scene, verbose=burg_params.view_simulation)
            utils.remove_objects()
            utils.load_objects(scene)
            utils.check_status(scene)
            utils.trigger_display_update(burg_params)
            return {'FINISHED'}
        else:
            print('Open object library first.')
            return {'CANCELLED'}


class BURG_OT_update_scene(bpy.types.Operator):
    bl_idname = "burg.update_scene"
    bl_label = "Update Scene"

    def execute(self, context):
        global scene
        if scene:
            utils.update_scene(scene)
            burg_params = bpy.context.scene.burg_params
            utils.simulate_scene(scene, verbose=burg_params.view_simulation)
            utils.update_objects(scene)
            utils.check_status(scene)
            utils.trigger_display_update(burg_params)
            return{'FINISHED'}
        else:
            print("Create a scene first.")
            return {'CANCELLED'}


class BURG_OT_lock_objects(bpy.types.Operator):
    bl_idname = "burg.lock_objects"
    bl_label = "Restricted"

    def set_transform_lock(object=None, enabled=False):
        if object:
            object.lock_location[2] = enabled
            object.lock_rotation_euler[0] = enabled
            object.lock_rotation_euler[1] = enabled

    def execute(self, context):
        burg_params = context.scene.burg_params
        if burg_params.lock_transform:
            for o in bpy.data.collections["objects"].objects:
                set_transform_lock(o, True)
                burg_params.lock_transform = True
        else:
            # unlock transformation retsirctions
            for o in bpy.data.collections["objects"].objects:
                set_transform_lock(o, False)
                burg_params.lock_transform = False
        return{'FINISHED'}


class BURG_OT_load_object_library(bpy.types.Operator):
    """ Loading object library information """

    bl_idname = "burg.load_object_library"
    bl_label = "Load Object Library"
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default="*.yaml")
    loaded: bpy.props.BoolProperty(name="loaded", default=False)

    def execute(self, context):
        global object_library

        try:
            # TODO: Error handling when opening incomplete/not processed library file.
            object_library = burg.ObjectLibrary.from_yaml(self.filepath)
            burg_params = context.scene.burg_params
            burg_params.object_library_file = self.filepath
            return {'FINISHED'}
        except Exception:
            print(f"Could not open burg object library: {self.filepath}.")
            return {'CANCELLED'}

    def invoke(self, context, event):
        # set filepath with default value of property
        self.filepath = self.filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class BURG_PT_setup_gui_VIEW_3D(bpy.types.Panel):
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
        flow = layout.grid_flow(row_major=True, columns=0,
                                even_columns=True, even_rows=False, align=True)

        burg_params = scene.burg_params
        layout.label(text="Config:")
        row = layout.row()
        row.enabled = False
        row.prop(burg_params, "object_library_file")
        row = layout.row()
        row.operator("burg.load_object_library", text='Open')
        col = layout.column()
        col.separator()
        layout.label(text="Creation:")
        row = layout.row()
        row.prop(burg_params, "number_objects")
        row = layout.row()
        row.prop(burg_params, "number_instances")
        row = layout.row()
        row.prop(burg_params, "view_simulation")
        row = layout.row()
        row.operator("burg.create_scene")
        layout.label(text="Verification:")
        row = layout.row()
        row.operator("burg.update_scene")
        row = layout.row()
        row.prop(burg_params, "view_mode", text="Display", expand=True)
        row = layout.row()
        row.prop(burg_params, "lock_transform")


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


def register():
    bpy.utils.register_class(BURG_PT_setup_gui_VIEW_3D)
    bpy.utils.register_class(BURG_OT_create_scene)
    bpy.utils.register_class(BURG_OT_update_scene)
    bpy.utils.register_class(BURG_OT_load_object_library)
    bpy.utils.register_class(BURG_PG_params)

    bpy.types.Scene.burg_params = bpy.props.PointerProperty(
        type=BURG_PG_params)


def unregister():
    bpy.utils.unregister_class(BURG_PT_setup_gui_VIEW_3D)
    bpy.utils.unregister_class(BURG_OT_create_scene)
    bpy.utils.unregister_class(BURG_OT_update_scene)
    bpy.utils.unregister_class(BURG_OT_load_object_library)
    bpy.utils.unregister_class(BURG_PG_params)

    del bpy.types.Scene.burg_params


if __name__ == "__main__":
    register()
