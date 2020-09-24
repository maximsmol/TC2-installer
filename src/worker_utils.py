from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QThread

def create_threaded(worker_fn, cb, args_classes, result_classes):
  class Worker(QObject):
    result_signal = QtCore.pyqtSignal(*result_classes)

    def __init__(self, parent=None):
      super(self.__class__, self).__init__(parent)

    @QtCore.pyqtSlot(*args_classes)
    def work(self, *args):
      self.result_signal.emit(worker_fn(*args))

  class Threaded(QObject):
    request_signal = QtCore.pyqtSignal(*args_classes)

    def __init__(self, parent=None):
      super(self.__class__, self).__init__(parent)

      self.worker = Worker()
      self.thread = QThread()
      self.worker.moveToThread(self.thread)
      self.thread.start()

      self.request_signal.connect(self.worker.work)
      self.worker.result_signal.connect(self.callback)

    @QtCore.pyqtSlot(*result_classes)
    def callback(self, *args):
      cb(*args)

    def submit(self, *args):
      self.request_signal.emit(*args)

  return Threaded
