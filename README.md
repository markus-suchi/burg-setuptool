# Setup GUI for BURG toolkit

This is a blender addon which provides a GUI for creating burg-toolkit setup templates.

## installation
### development
- Clone the repository using recursive. 
```
git clone --recursive git@github.com:markus-suchi/burg-toolkit-gui.git [dest-dir]
```
- Download [blender 2.92](https://download.blender.org/release/Blender2.92/) for your platform and extract it.
- Locate blenders addon folder (<extract dir>/2.92/scripts/addons) ***create a link*** to this repository root dir.
- Locate and change to blenders python folder (<extract dir>/2.92/python/bin)
- Enable pip for blender using the shipped python package of blender
```
./python3.7m -m ensurepip
./python3.7m -m pip install --upgrade pip
./python3.7m --upgrade setuptools wheel
```
- Install all dependencies from burg-toolkit into blender local python package storage.
```
./python3.7m -m pip install -e  <path to repository>/burg-toolkit/setup.py
```
### packaged addon
TODO

## enable addon
- Start blender
- Choose "Edit -> Preferences... ->Add-ons"
- Select "Testing" Tab at the top
- Click on the checkbox for "User Interface: BURG toolkit-Setup GUI"
- Check console for any errors

## start template creation
- Choose "File -> New -> BURG Setup Template"
- In the main window to the top right expand the Property Window
- Select "BURG Setup Template"
- "Open" an object library yaml File
- Adjust settings
- Click "Create Random Scene"
