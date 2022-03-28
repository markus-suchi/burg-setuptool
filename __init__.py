bl_info = {
    "author": "Markus Suchi",
    "name": "BURG-SetupTool",
    "description": "GUI for creating BURG setup templates.",
    "warning": "",
    "version": (0, 2),
    "blender": (2, 92, 0),
    "support": 'TESTING',
    "category": 'User Interface'
}

if "bpy" in locals():
    print("bpy in locals")
    import importlib
    importlib.reload(burg_setup_gui)
else:
    import os
    import shutil
    import sys


    # --- create the startup file for the burg setup gui ---
    script_file = os.path.abspath(__file__)
    addon_dir = os.path.dirname(script_file)

    addon_dir_link, _ = os.path.split(os.path.dirname(__file__))
    script_dir, _ = os.path.split(addon_dir_link)
    startup_dir = os.path.join(
        script_dir, 'startup', 'bl_app_templates_system')
    burg_setup_gui_startup_dir = os.path.join(
        startup_dir, 'BURG_Setup_Template')
    burg_setup_gui_startup_file = os.path.join(
        burg_setup_gui_startup_dir, 'startup.blend')
    burg_setup_gui_startup_file_source = os.path.join(
        addon_dir, 'burg-toolkit-setup-gui', 'burg_setup_gui.blend')

    if os.path.exists(startup_dir):
        if not os.path.exists(burg_setup_gui_startup_dir):
            os.mkdir(burg_setup_gui_startup_dir)
        shutil.copyfile(burg_setup_gui_startup_file_source,
                        burg_setup_gui_startup_file)
    else:
        print(f"Startup dir {startup_dir} does not exist")

    # --- create the startup file for the burg setup gui ---
    sys.path.append(os.path.join(addon_dir, 'burg-toolkit'))
    sys.path.append(os.path.join(addon_dir, 'burg-toolkit-setup-gui'))

    import burg_setup_gui

#### REGISTER ###


def register():
    burg_setup_gui.register()


def unregister():
    burg_setup_gui.unregister()


if __name__ == "__main__":
    register()
