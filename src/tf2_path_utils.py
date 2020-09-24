import sys
import os
import json
from pathlib import Path

tf2_path_lineedit = [None]

def full_tf2_path():
  return os.path.expanduser(tf2_path_lineedit[0].text())

with (Path(__file__).parent / 'tf2_paths.txt').open('r') as f:
  all_tf2_paths = json.load(f)

def count_files(schema):
  res = 0
  for k, v in schema.items():
    if v is None:
      res += 1
    else:
      res += count_files(v)
  return res
expected_tf2_files = count_files(all_tf2_paths)

def tf2_path_sanity_check(x, fast=False):
  if not fast:
    def check(schema, p):
      for k, v in schema.items():
        if not (p / k).exists():
          print(f'TF2 path sanity check failed: {p/k} is missing.')
          return False
        if v is None:
          continue
        if not check(v, p / k):
          return False
      return True
    return check(all_tf2_paths, Path(x))
  return (Path(x) / 'tf' / 'bin' / 'client.so').exists()

default_path_and_broken = False

def set_tf2_path(new_path, default_path=False):
  x = Path(os.path.expanduser(new_path))
  if not tf2_path_sanity_check(x, fast=True):
    print(f'TF2 path {x} seems to be wrong. Trying to guess a better one.')

    done = False
    if not done and x.parts[-1] == 'common':
      new_x = x / 'Team Fortress 2'
      if tf2_path_sanity_check(new_x, fast=True):
        done = True
        x = new_x
        print('Guessed that `steamapps/common` was selected instead.')
    if not done and x.parts[-1] == 'steamapps':
      new_x = x / 'common' / 'Team Fortress 2'
      if tf2_path_sanity_check(new_x, fast=True):
        done = True
        x = new_x
        print('Guessed that `steamapps` was selected instead.')
    if not done and x.parts[-1].lower() == 'steam':
      new_x = x / 'steamapps' / 'common' / 'Team Fortress 2'
      if tf2_path_sanity_check(new_x, fast=True):
        done = True
        x = new_x
        print('Guessed that Steam root was selected instead.')
    if not done and x.parts[-1].lower() == 'tf':
      new_x = x.parent
      if tf2_path_sanity_check(new_x, fast=True):
        done = True
        x = new_x
        print('Guessed that `Team Fortress 2/tf` was selected instead.')
    if not done:
      print('Out of options, none of the guesses worked.')


  if not tf2_path_sanity_check(x):
    warn_title = 'Invalid TF2 Path'
    warn_msg = (
      'The specified TF2 install directory is missing '
      'contain some of the expected files.\n\n'
      'This probably means that you selected the wrong '
      'TF2 install directory.\n\n'
      'Double-check your selection and proceed only if '
      'absolutely certain it is correct.')

    if default_path:
      default_path_and_broken = True
      warn_title = 'Could Not Guess TF2 Path'
      warn_msg = (
        'Tried to guess the TF2 install path but the directory is missing '
        'some of the expected files.\n\n'
        'You should select the TF2 install directory manually since '
        'the installer will probably fail otherwise.')

    QMessageBox(QMessageBox.Warning, warn_title, warn_msg).exec_()

  new_path = str(x).replace(os.path.expanduser('~'), '~', 1)
  tf2_path_lineedit[0].setText(new_path)

tf2_default_path = '~/'
if sys.platform == 'linux':
  tf2_default_path = '~/.steam/steam/steamapps/common/Team Fortress 2/'
elif sys.platform == 'win32':
  import winreg
  try:
    hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\WOW6432Node\\Valve\\Steam')
    steam_path = winreg.QueryValueEx(hkey, "InstallPath")[0]
    tf2_default_path = Path(steam_path) / 'steamapps' / 'common' / 'Team Fortress 2'
    winreg.CloseKey(hkey)
  except:
    print('Could not read the Steam install location from registry.')
    print('Using a dumb default.')
    tf2_default_path = Path(__file__).drive / 'Program Files' / 'Steam' / 'steamapps' / 'common' / 'Team Fortress 2'
elif sys.platform == 'darwin':
  tf2_default_path = '~/Library/Application Support/Steam/steamapps/common/Team Fortress 2'
else:
  print(f'No default guess for TF2 install directory for platform {sys.platform}.')
def set_default_path():
  set_tf2_path(tf2_default_path, default_path=True)
