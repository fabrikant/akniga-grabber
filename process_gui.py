from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import QProcess
from PyQt5.QtGui import QTextCursor


class ProcessWindow(QMdiSubWindow):

    def __init__(self, url, path):
        super(ProcessWindow, self).__init__()
        self.process = None
        self.url = url
        self.path = path
        uic.loadUi('ui/process.ui', self)
        self.manage_form()

    def print_message(self, data):
        stdout = bytes(data).decode("utf8")
        if not "" == stdout:
            self.textConsole.moveCursor(QTextCursor.End)
            self.textConsole.insertPlainText(stdout)
            self.textConsole.moveCursor(QTextCursor.End)

    def on_stdout(self):
        self.print_message(self.process.readAllStandardOutput())

    def on_stderr(self):
        self.print_message(self.process.readAllStandardError())

    def on_finished(self):
        exitcode = self.process.exitCode()
        self.textConsole.append("Process finished with exit code: {0}".format(exitcode))
        if exitcode == 0:
            self.textConsole.append("Path: {0}".format(self.path))

    def manage_form(self):
        geom = self.geometry()
        title_height = self.style().pixelMetric(QStyle.PM_TitleBarHeight)
        self.textConsole.setGeometry(2, title_height + 2, geom.width() - 4, geom.height() - title_height - 4)
        self.setWindowTitle(str(self.url))

    def resizeEvent(self, event):
        self.manage_form()
        return super(ProcessWindow, self).resizeEvent(event)

    def closeEvent(self, event):
        if self.process is not None:
            self.process.kill()
        return super(ProcessWindow, self).closeEvent(event)

    def showEvent(self, show_event):
        if self.process is None:
            self.textConsole.append("Waiting for start...")
            self.process = QProcess()
            self.process.readyReadStandardOutput.connect(self.on_stdout)
            self.process.readyReadStandardError.connect(self.on_stderr)
            self.process.finished.connect(self.on_finished)
            try:
                command = ['akniga_dl.py', self.url, self.path]
                self.process.start("python", command)
            except Exception as error:
                self.textConsole.append(f"{error}")

