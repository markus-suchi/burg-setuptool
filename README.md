# Setup GUI for BURG toolkit

This is a blender addon which provides a GUI for creating burg-toolkit setup templates.

# installation of burg-toolkit-gui

## install blender

We specifically require version 2.92. Other versions unfortunately do not work, due to compatibility issues.

Download and extract blender 2.92:
```
cd ~
wget https://download.blender.org/release/Blender2.92/blender-2.92.0-linux64.tar.xz
tar -xf blender-2.92.0-linux64.tar.xz
rm blender-2.92.0-linux64.tar.xz
```

If you extract to any other location you will need to adjust the paths accordingly throughout these installation instructions.

Optionally, you can make blender callable from the app menu and/or from the command line. Note that you only see console outputs when you start it from command line. However, seeing these outputs is generally not required and only useful for debugging.

Make blender callable in the app menu:
- Open `~/blender-2.92.0-linux64/blender.desktop`, change entries:
	- `Exec=/home/username/blender-2.92.0-linux64/blender %f`
	- `Icon=/home/username/blender-2.92.0-linux64/blender.svg`
	- `Name=Blender292`
- `cp ~/blender-2.92.0-linux64/blender.desktop ~/.local/share/applications`

Make blender callable in the command line:
- `sudo ln -s ~/blender-2.92.0-linux64/blender /usr/local/bin/blender292`

## install setup tool as blender addon

Clone the repository, add it to blender add ons:
```
cd ~
git clone --recursive git@github.com:markus-suchi/burg-toolkit-gui.git
cd blender-2.92.0-linux64/2.92/scripts/addons
ln -s ~/burg-toolkit-gui/ burg-toolkit-gui
```

Install dependencies in blender python:
```
cd ~/blender-2.92.0-linux64/2.92/python/bin
./python3.7m -m ensurepip
./python3.7m -m pip install --upgrade pip
./python3.7m -m pip install --upgrade setuptools wheel
./python3.7m -m pip install ~/burg-toolkit-gui/burg-toolkit['collision']
```

### activate the blender addon
- Start blender, either from command line (see debug outputs) or from the app menu, as configured before
- Open "Edit" -> "Preferences..."
- Go to "Add-ons", activate "Testing" tab at the top
- Click on the checkbox to activate "User Interface: BURG toolkit-Setup GUI" and close preferences

This concludes the installation.

## upgrade

If you want to upgrade to a new version, these steps are required:
```
# fetch changes to gui and toolkit
cd burg-toolkit-gui
git pull
git submodule update --recursive

# rebuild toolkit
cd ~/blender-2.92.0-linux64/2.92/python/bin
./python3.7m -m pip install ~/burg-toolkit-gui/burg-toolkit['collision']
```

## usage

- Choose "File" -> "New" -> "BURG Setup Template"
- In the main window to the top right expand the Property Window
- Select "BURG Setup Template" to see the addon menu

Get started by:
- Opening an object library yaml file and then composing scenes, or
- Importing a scene, which automatically loads an object library

Rotating the view:
- use num pad to rotate
- click and hold on the coordinate system at the top right corner to rotate
