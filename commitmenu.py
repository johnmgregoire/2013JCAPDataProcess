# Allison Schubauer and Daisy Hernandez
# Created: 6/25/2013
# Last Updated: 6/26/2013
# For JCAP

import sys, os
from PyQt4 import QtCore, QtGui
from time import strftime, localtime
import re

class MainMenu(QtGui.QMainWindow):
    def __init__(self):
        super(MainMenu, self).__init__()
        self.versionName = None
        self.verifiedName = None
        self.initUI()

    """ initializes the user interface for this commit menu """
    def initUI(self):
        self.setGeometry(500, 200, 600, 100)
        self.setWindowTitle('Data Analysis File Committer')

        self.mainWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.secondaryWidget = QtGui.QWidget(self)

        self.mainLayout= QtGui.QGridLayout()
        self.secondaryLayout= QtGui.QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)
        self.secondaryWidget.setLayout(self.secondaryLayout)

        self.directions = QtGui.QLabel('Please select the folder you wish to.', self)
        self.mainLayout.addWidget(self.directions, 0,0)
        self.mainLayout.addWidget(self.secondaryWidget)

        selectFolder = QtGui.QPushButton('Select Folder', self)
        selectFolder.clicked.connect(self.selectProgram)
        self.secondaryLayout.addWidget(selectFolder, 0, 0)

        self.fileSelected = QtGui.QLineEdit(self)
        self.fileSelected.setReadOnly(True)
        self.secondaryLayout.addWidget(self.fileSelected, 0, 1)

        self.status = QtGui.QLabel('', self)
        self.mainLayout.addWidget(self.status)

        self.show()

    """ textFileTuple is signal received from file dialog; 0th item is string of
    file/folder names to display in line edit, 1st item is list of filepaths
    (basenames) to load """
    def loadData(self, textFileTuple):
        self.fileSelected.setText(textFileTuple[0])
        self.files = textFileTuple[1]
        print len(self.files)

    """ deals with getting relevent information for the file ones wishes to commit """
    def selectProgram(self):
        self.programDialog = QtGui.QFileDialog(self,
                                               caption = "Select a version folder containing data analysis scripts")
        self.programDialog.setFileMode(QtGui.QFileDialog.Directory)
        # if user clicks 'Choose'
        if self.programDialog.exec_():
            self.status.setText('')
            # list of QStrings (only one folder is allowed to be selected)
            dirList = self.programDialog.selectedFiles()
            targetDir = os.path.normpath(str(dirList[0]))
            pyFiles = filter(lambda f: f.endswith('.py'), os.listdir(targetDir))
            # set the line edit and get save the location of the pyFiles
            self.loadData(tuple((targetDir,pyFiles)))
            print pyFiles
            # is the name valid with our version naming standards
            nameValidity = self.versionNameVerifier(targetDir)
            # if a file's name was invalid to commit
            if nameValidity[0] == False:
                # deals with renaming the program
                newTargetDir = self.renameProgram(targetDir,nameValidity[1])
                pyFiles = filter(lambda f: f.endswith('.py'), os.listdir(newTargetDir))
                self.loadData(tuple((newTargetDir,pyFiles)))
            if nameValidity[0] is not None:
                self.status.setText('Your file has been committed.')

    """ verifies that the name of the new version folder matches the standard naming """       
    def versionNameVerifier(self,directory):
        plainDirectory = os.path.dirname(directory)
        self.versionName = os.path.basename(directory)
            
        dateExpected = strftime("%Y%m%d", localtime())
        pattern = '^v(' + dateExpected + ')([0-9])$'
        result = re.match(pattern, self.versionName)

        # go through all the valid names to check if either we have a match or we must
        # renaming the name of the folder
        for x in range(0,10):
            pathToTest = os.path.join(plainDirectory, 'v' + dateExpected + str(x))
            try:
                if os.path.exists(pathToTest):
                    if directory == pathToTest and result:
                        return (True,None)
                    else:
                        pass
                else:
                    return (False,pathToTest)
            except:
                print "TODO Something must have really gone wrong - put a logger maybe?"
                
        print "It appears you might have done more than 10 commits in one day. \
We thus cannot commit your file. Please refrain from doing this in the future."
        return (None,None)
       

    """ deals with renaming the program with a valid name """
    def renameProgram(self, oldpath, newpath):
        newPath = os.path.normpath(newpath)
        oldPath = os.path.normpath(oldpath)
        os.rename(oldPath,newPath)
        return newPath

def main():
    app = QtGui.QApplication(sys.argv)
    menu = MainMenu()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
