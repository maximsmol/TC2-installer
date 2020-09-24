import json
import os
from pathlib import Path

res = {}

root = Path(os.path.expanduser('~/.steam/steam/steamapps/common/Team Fortress 2/'))
def work(cur, p, indent=0):
  for sub in p.iterdir():
    print(f'{"  " * indent}Reading {sub.name}')
    if sub.is_dir():
      cur[sub.name] = {}
      work(cur[sub.name], sub, indent + 1)
    else:
      cur[sub.name] = None

work(res, root)

with (Path(__file__).parent / 'tf2_paths.txt').open('w') as f:
  json.dump(res, f, indent=2)
