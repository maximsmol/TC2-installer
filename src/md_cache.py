import pickle
from pathlib import Path

import requests

from file_base import file_base
from worker_utils import create_threaded

md_cache = {}
md_cache_path = file_base / 'md_cache.pkl'
if md_cache_path.exists():
  with md_cache_path.open('rb') as f:
    try:
      md_cache = pickle.load(f)
      print(f'Loaded Markdown cache with {len(md_cache)} entries.')
    except:
      print('Failed to load Markdown cache. Ignoring...')

def get_md(release):
  if release['id'] in md_cache:
    return '<div class="markdown-body">' + md_cache[release['id']] + '</div>'

  res = requests.post('https://api.github.com/markdown', json=dict(text=release['body'], context='mastercomfig/team-comtress-2')).text
  md_cache[release['id']] = res

  with md_cache_path.open('wb') as f:
    pickle.dump(md_cache, f)

  return '<div class="markdown-body">' + res + '</div>'

def getMdFetcher(widget):
  return create_threaded(lambda release: get_md(release),
                         lambda res: widget.setHtml(res),
                         [dict],
                         [str])()
