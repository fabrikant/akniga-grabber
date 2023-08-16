from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import QProcess
from akniga_dl import download_book as download


class ProcessWindow(QMdiSubWindow):

    def __init__(self, url, path):
        super(ProcessWindow, self).__init__()
        self.url = url
        self.path = path
        uic.loadUi('ui/process.ui', self)
        self.manage_form()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        self.process.finished.connect(self.on_finished)
        try:
            command = ['akniga_dl.py', self.url, self.path]
            self.process.start("python", command)
        except Exception as error:
            self.textConsole.append(f"{error}")

    def on_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.textConsole.append(stdout)

    def manage_form(self):
        geom = self.geometry()
        title_height = self.style().pixelMetric(QStyle.PM_TitleBarHeight)
        self.textConsole.setGeometry(2, title_height + 2, geom.width() - 4, geom.height() - title_height - 4)
        self.setWindowTitle(str(self.url))

    def resizeEvent(self, event):
        self.manage_form()
        return super(ProcessWindow, self).resizeEvent(event)

    def closeEvent(self, event):
        self.process.kill()
        return super(ProcessWindow, self).closeEvent(event)

    def on_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.textConsole.append(stderr)

    def on_finished(self):
        self.textConsole.append("Process finished with exit code: {0}".format(self.process.exitCode()))
