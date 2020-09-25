from pathlib import Path
import sys

file_base = Path(__file__).parent
if hasattr(sys, '_MEIPASS'):
  file_base = Path(sys._MEIPASS)
  print(f'We appear to be running from a PyInstaller package at `{file_base}`.')
