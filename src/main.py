import sys
import os
import json
from pathlib import Path
import dateutil.parser as dp
import signal
import shutil
import zipfile
from threading import Lock, Event
import time

import requests
from PyQt5 import QtCore
from PyQt5.QtCore import QUrl, QObject, QThread, Qt
from PyQt5.QtGui import QColorConstants, QPalette, QIcon
from PyQt5.QtWidgets import \
  QApplication, \
  QMainWindow, \
  QComboBox, \
  QFileDialog, \
  QPushButton, \
  QWidget, \
  QGridLayout, \
  QHBoxLayout, \
  QVBoxLayout, \
  QLineEdit, \
  QMessageBox, \
  QLabel, \
  QTextBrowser, \
  QProgressBar

from md_cache import getMdFetcher

debug = False

releases = []
release_cache = Path(__file__).parent / 'releases_cache.json'
if debug:
  if release_cache.exists():
    with release_cache.open('r') as f:
      releases = [json.load(f)]

# TODO: fetch releases in a thread
releases = requests.get('https://api.github.com/repos/mastercomfig/team-comtress-2/releases').json()
# TODO: master should work, maybe also specific commits, other branches, and all tags
# releases += [{'__special': 'master', 'name': 'master'}]

if debug:
  with release_cache.open('w') as f:
    json.dump(releases, f)

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(str(Path(__file__).parent.parent / 'icon.png')))
if sys.platform == 'win32':
  import ctypes
  ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'maximsmol.tc2installer')

win = QMainWindow()
main = QWidget()
win.setCentralWidget(main)
main_layout = QGridLayout(main)

version_select_layout = QVBoxLayout()
main_layout.addLayout(version_select_layout, 0, 0, 1, -1)
version_layout = QHBoxLayout()
version_select_layout.addLayout(version_layout)
version_label = QLabel('Team Comtress 2 Version:')
version_list = QComboBox()
version_layout.addWidget(version_label)
version_layout.addWidget(version_list)

version_date_label = QLabel()
version_layout.addWidget(version_date_label)
version_layout.addStretch(2)

# changelog_palette = QPalette()
# changelog_palette.setColor(QPalette.Base, QColorConstants.White)
changelog = QTextBrowser()
changelog.setOpenExternalLinks(True)
# changelog.setPalette(changelog_palette)
# with (Path(__file__).parent / 'gh_markdown.css').open('r') as f:
#   changelog.document().setDefaultStyleSheet(f.read())
# changelog.setReadOnly(True)
version_select_layout.addWidget(changelog)
changelogFetcher = getMdFetcher(changelog)

from md_cache import get_md
def select_version(i):
  version_list.setCurrentIndex(i)
  release = releases[i]

  if '__special' in release:
    if release['__special'] != 'master':
      raise ValueError('Unknown __special release')

    # TODO: fetch timestamp
    version_date_label.setText('Last updated: no timestamp available')
    # TODO: fetch commits since last release?
    changelog.setHtml('<h1>No changelog available for master</h1>')
    return

  version_date_label.setText('Published on: ' + dp.isoparse(release['published_at']).strftime('%x'))
  changelogFetcher.submit(release)
version_list.currentIndexChanged.connect(select_version)

# this is for async updating of the release list in the future
def upd_releases():
  version_list.clear()
  for r in releases:
    version_list.addItem(r['name'])
  select_version(0)
upd_releases()

tf2_path_label = QLabel('TF2 Path:')
main_layout.addWidget(tf2_path_label, 1, 0)

tf2_path = QLineEdit()
main_layout.addWidget(tf2_path, 1, 1)

from tf2_path_utils import \
  tf2_path_lineedit, set_tf2_path, set_default_path, full_tf2_path, \
  tf2_default_path, expected_tf2_files
tf2_path_lineedit[0] = tf2_path
set_default_path()

def select_tf2_cb():
  dialog = QFileDialog()
  dialog.setDirectory(full_tf2_path())
  dialog.setFileMode(QFileDialog.Directory)
  dialog.setOption(QFileDialog.ShowDirsOnly)

  sidebar = dialog.sidebarUrls()
  sidebar += [QUrl.fromLocalFile(os.path.expanduser(tf2_default_path))]
  dialog.setSidebarUrls(sidebar)

  dialog.exec_()

  set_tf2_path(dialog.selectedFiles()[0])

select_tf2_btn = QPushButton('Browse…')
select_tf2_btn.clicked.connect(select_tf2_cb)
main_layout.addWidget(select_tf2_btn, 1, 2)


install_path_label = QLabel('Install path:')
main_layout.addWidget(install_path_label, 2, 0)

install_path = QLineEdit()
main_layout.addWidget(install_path, 2, 1)
if sys.platform == 'linux':
  install_path.setText('~/Team Comtress 2/')
elif sys.platform == 'win32':
  install_path.setText(Path(__file__).drive / 'Team Comtress 2')
elif sys.platform == 'darwin':
  install_path.setText('~/Team Comtress 2')
else:
  print(f'No default guess for install directory for platform {sys.platform}.')

def select_install_cb():
  existing_parent = os.path.expanduser(install_path.text())
  p = Path(existing_parent)
  while not p.exists():
    p = p.parent
  existing_parent = str(p)

  dialog = QFileDialog()
  dialog.setDirectory(existing_parent)
  dialog.setFileMode(QFileDialog.Directory)
  dialog.setOption(QFileDialog.ShowDirsOnly)

  dialog.exec_()

  new_path = dialog.selectedFiles()[0].replace(os.path.expanduser('~'), '~', 1)
  install_path.setText(new_path)

select_install_btn = QPushButton('Browse…')
select_install_btn.clicked.connect(select_install_cb)
main_layout.addWidget(select_install_btn, 2, 2)

safe_cfgs = []
with (Path(__file__).parent / 'safe_cfgs.txt').open('r') as f:
  safe_cfgs = [x.strip() for x in f.readlines() if x.strip() != '']

def rm(x):
  if x.is_dir():
    shutil.rmtree(x)
    return
  x.unlink(missing_ok=True)
class TC2InstallWorker(QObject):
  status_signal = QtCore.pyqtSignal(float, str)

  def __init__(self, parent=None):
    super(self.__class__, self).__init__(parent)

    self.running_lock = Lock()
    self._running = False

  @property
  def running(self):
    with self.running_lock:
      return self._running

  @running.setter
  def running(self, val):
    with self.running_lock:
      self._running = val

  def print_status(self, done_percent, msg):
    print(f'{done_percent * 100:>3.0f}%: {msg}')
    self.status_signal.emit(done_percent, msg)

  @QtCore.pyqtSlot()
  def work(self):
    self.running = True

    src = full_tf2_path()
    src_p = Path(src)
    dst = os.path.expanduser(install_path.text())
    dst_p = Path(dst)

    dst_p.mkdir(parents=True, exist_ok=True)

    release = releases[version_list.currentIndex()]
    if '__special' in release and release['__special'] == 'master':
      raise ValueError('Not implemented')

    self.print_status(0.0, f'Downloading `game_clean.zip` for release {release["name"]}…')
    asset = None
    for a in release['assets']:
      if a['name'] != 'game_clean.zip':
        continue
      asset = a
      break
    if asset is None:
      QMessageBox(QMessageBox.Critical, 'Could Not Download Release',
                  'The selected version seems to not include `game_clean.zip`\n\n'
                  'Aborting installation.').exec_()
    print(f'Asset URL is: {asset["browser_download_url"]}')

    versioned_asset = dst_p / f'game_clean_{release["name"]}.zip'
    if versioned_asset.exists():
      print(f'Reusing existing download: `{versioned_asset}`.')
    else:
      print(f'Downloading `{versioned_asset}`.')
      with versioned_asset.open('wb') as f:
        f.write(requests.get(asset["browser_download_url"]).content)

    if not self.running:
      return

    self.print_status(0.1, f'Copying TF2 from {src_p.name} to {dst_p.name}…')
    files_copied = 0
    def sync_dir(fr, to, indent=0):
      nonlocal files_copied
      if not self.running:
        return

      to.mkdir(exist_ok=True)
      for x in fr.iterdir():
        if not self.running:
          return

        to_cur = to / x.name
        # TODO: is there a way to skip entire directories?
        if not x.is_dir() and to_cur.exists() and to_cur.lstat().st_mtime == x.lstat().st_mtime:
          print(f'{"  " * indent}SKIP {x.name}')
          continue

        print(f'{"  " * indent}Syncing {x.name}')
        if x.is_dir():
          sync_dir(fr / x.name, to_cur, indent + 1)
        else:
          self.print_status(0.1 + min(files_copied, expected_tf2_files)/expected_tf2_files*.8, f'Copying TF2 from {src_p.name} to {dst_p.name}: {x.name}…')
          shutil.copy2(x, to_cur)
          files_copied += 1

    # if dst_p.exists() and dst_p.lstat().st_mtime >= src_p.lstat().st_mtime:
    #   print(f'Skip sync, directory is already up-to-date')
    # else:
    sync_dir(src_p, dst_p)

    if not self.running:
      return

    self.print_status(0.9, f'Removing custom settings…')
    for f in (dst_p / 'tf' / 'custom').iterdir():
      if f.name == 'readme.txt':
        continue
      if f.name == 'workshop':
        for f1 in f.iterdir():
          rm(f1)
        continue

      shutil.rmtree(f)
    for f in (dst_p / 'tf' / 'cfg').iterdir():
      if f.name == 'unencrypted':
        for f1 in f.iterdir():
          rm(f1)
        continue
      if f.name in safe_cfgs:
        continue
      rm(f)

    self.print_status(0.95, f'Extracting {versioned_asset}…')
    time.sleep(1)
    with zipfile.ZipFile(versioned_asset, 'r') as f:
      f.extractall(dst_p)

    self.print_status(1.0, 'Done!')


added_progress_info = [False]
progress_info = QVBoxLayout()

install_pb = QProgressBar()
progress_info.addWidget(install_pb)

install_status = QLabel()
install_status.setAlignment(Qt.AlignHCenter)
progress_info.addWidget(install_status)

class TC2Installer(QObject):
  run_worker_signal = QtCore.pyqtSignal()

  def __init__(self, parent=None):
    super(self.__class__, self).__init__(parent)

    self.worker = TC2InstallWorker()
    self.thread = QThread()
    self.worker.moveToThread(self.thread)
    self.thread.start()

    self.run_worker_signal.connect(self.worker.work)
    self.worker.status_signal.connect(self.update_status)

  @QtCore.pyqtSlot(float, str)
  def update_status(self, done_percent, message):
    install_pb.setValue(done_percent * 100)
    install_status.setText(message)

  def run(self):
    self.worker.running = False
    # this is queued by Qt
    self.run_worker_signal.emit()


installer = TC2Installer()
def install_tc2_cb():
  if not added_progress_info[0]:
    main_layout.addLayout(progress_info, 3, 0, 1, -1)
    added_progress_info[0] = True
  installer.run()

install_btn = QPushButton('Install')
install_btn.clicked.connect(install_tc2_cb)
main_layout.addWidget(install_btn, 2, 3)

win.setWindowTitle('Team Comtress 2 Installer')
win.resize(800, 600)
win.show()

# def sigint_handler(*args):
#   QApplication.quit()
# signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGINT, signal.SIG_DFL)
app.exec_()
