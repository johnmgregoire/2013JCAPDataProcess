# Allison Schubauer and Daisy Hernandez
# 6/20/2013
# PyQt4-powered GUI for starting the automated data processor

import sys, os
from PyQt4 import QtCore, QtGui
import fomautomator

class MainMenu(QtGui.QMainWindow):
    def __init__(self):
        super(MainMenu, self).__init__()
        self.program = None
        self.initUI()

    def initUI(self):
        self.setGeometry(500, 200, 500, 600)
        self.setWindowTitle('Data Analysis Automator')

        self.mainWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.mainWidget)

        self.mainLayout = QtGui.QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)

        selectFiles = QtGui.QPushButton('Select Data Files', self)
        selectFiles.clicked.connect(self.selectData)
        self.mainLayout.addWidget(selectFiles, 0, 0)

        self.fileSelected = QtGui.QLineEdit(self)
        self.fileSelected.setReadOnly(True)
        self.mainLayout.addWidget(self.fileSelected, 0, 1)

        selectProgFolder = QtGui.QPushButton('Select Program', self)
        selectProgFolder.clicked.connect(self.selectProgram)
        self.mainLayout.addWidget(selectProgFolder, 1, 0)

        self.progSelected = QtGui.QLineEdit(self)
        self.progSelected.setReadOnly(True)
        self.mainLayout.addWidget(self.progSelected, 1, 1)

        runButton = QtGui.QPushButton('Run', self)
        runButton.clicked.connect(self.startAutomation)
        self.mainLayout.addWidget(runButton, 2, 0)

        self.show()

    def selectData(self):
        self.datafileDialog = MultipleFileDialog()
        self.datafileDialog.filesSelected.connect(self.loadData)
        if self.datafileDialog.isHidden():
            self.datafileDialog = None

    """ textFileTuple is signal received from file dialog; 0th item is string of
        file/folder names to display in line edit, 1st item is list of filepaths
        to load """
    def loadData(self, textFileTuple):
        self.fileSelected.setText(textFileTuple[0])
        self.files = textFileTuple[1]
        print len(self.files)
        print self.files

    def selectProgram(self):
        self.programDialog = QtGui.QFileDialog(self,
                                               caption = "Select a version folder containing data analysis scripts")
        self.programDialog.setFileMode(QtGui.QFileDialog.Directory)
        # if user clicks 'Choose'
        if self.programDialog.exec_():
            # list of QStrings (only one folder is allowed to be selected)
            dirList = self.programDialog.selectedFiles()
            targetDir = str(dirList[0])
            self.progSelected.setText(targetDir)
            pyFiles = filter(lambda f: f.endswith('.py'), os.listdir(targetDir))
            # THIS IS TEMPORARY
            self.progModule = [mod[:-3] for mod in pyFiles if
                               mod == 'fomfunctions_firstversion.py'][0]

    def startAutomation(self):
        if self.progModule:
            self.automator = fomautomator.FOMAutomator(self.files, self.progModule)
            self.automator.runSequentially()
        else:
            # raise error dialog that no version has been selected -
            #   alternatively, don't make "run" button clickable until
            #   version folder has been selected
            pass
        

""" copied (basically) from StackOverflow:
    http://stackoverflow.com/questions/6484793/
    multiple-files-and-folder-selection-in-a-qfiledialog """
class MultipleFileDialog(QtGui.QFileDialog):

    filesSelected = QtCore.pyqtSignal(tuple)
    
    def __init__(self):
        super(MultipleFileDialog, self).__init__()
        self.setOption(self.DontUseNativeDialog, True)
        self.setFileMode(self.ExistingFiles)
        defaultButtons = self.findChildren(QtGui.QPushButton)
        self.openButton = [button for button in defaultButtons if "Open" in
                           str(button.text())][0]
        self.openButton.clicked.disconnect()
        self.openButton.clicked.connect(self.openClicked)
        self.tree = self.findChild(QtGui.QTreeView)
        self.nameLine = self.findChild(QtGui.QLineEdit)
        self.tree.selectionModel().selectionChanged.disconnect()
        self.tree.selectionModel().selectionChanged.connect(self.showSelection)
        self.show()

    """ shows name(s) of currently selected files/folders in the
        filename bar in the dialog """
    def showSelection(self):
        self.selInds = self.tree.selectionModel().selectedIndexes()
        selItems = []
        for index in self.selInds:
            # selInds is array of rows and columns - each row is
            #   a selected item; columns hold information about the
            #   items.  Column 0 is the folder/file name.
            if index.column() == 0:
                selItems.append(str(index.data().toString()))
        self.selText = ', '.join(selItems)
        self.nameLine.setText(self.selText)

    """ sends list of all .txt files that were selected to MainMenu """
    def openClicked(self):
        selFiles = []
        filesToOpen = []
        for index in self.selInds:
            if index.column() == 0:
                selFiles.append(str(self.directory().absoluteFilePath(index.data().toString())))
        for item in selFiles:
            if item.endswith('.txt'):
                filesToOpen.append(item)
            else:
                for root, dirs, files in os.walk(item):
                    selFiles.extend(files)
        # send string representation of selected files and list of
        #   filepaths to MainMenu (triggers loadData)
        self.filesSelected.emit((self.selText, filesToOpen))
        self.hide()
        

def main():
    app = QtGui.QApplication(sys.argv)
    menu = MainMenu()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
