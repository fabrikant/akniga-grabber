import sys
from process_gui import ProcessWindow
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtGui


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('ui/main.ui', self)
        self.processes = []

    def onButtonOpenPathClick(self):
        path = QFileDialog.getExistingDirectory(self, caption='Open directory')
        self.linePath.setText(path)

    def onButtonDownloadClick(self):
        sub_window = ProcessWindow(self.lineURL.text(), self.linePath.text())
        self.mdiArea.addSubWindow(sub_window)
        sub_window.show()

    def onButtonPaste(self):
        if 'akniga.org' in app.clipboard().text():
            self.lineURL.setText(app.clipboard().text())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
