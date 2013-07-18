# Allison Schubauer and Daisy Hernandez
# Created: 6/27/2013
# Last Updated: 7/18/2013
# For JCAP

import os
import sys

sys.path.append(os.path.expanduser("~/Documents/GitHub/JCAPPyDBComm"))

import re
import numpy
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
import fomautomator
import path_helpers
import mysql_dbcommlib 

from fomautomator import FUNC_DIR, XML_DIR
from rawdataparser import RAW_DATA_PATH

MOD_NAME = 'fomfunctions'
UPDATE_MOD_NAME = 'fomfunctions_update'

################################################################################
############################ echemvisDialog class ##############################
################################################################################

class echemvisDialog(QtGui.QMainWindow):

    """ handles all the initializing - currently does nothing with folderpath"""
    def __init__(self, parent=None, title='', folderpath=None):
        
        super(echemvisDialog, self).__init__()
        self.parent=parent
        self.paths = []
        self.progModule = None
        self.updateModule = None
        self.exptypes = []
        self.initDB()
        self.initUI()

    """ initializes the user interface """
    def initUI(self):
        
        self.setGeometry(300, 200, 150, 150)
        self.setWindowTitle('Processing Files')

        self.mainWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.mainWidget)

        self.mainLayout = QtGui.QGridLayout()
        self.mainWidget.setLayout(self.mainLayout)

        self.prog_label = QtGui.QLineEdit()
        self.message_label = QtGui.QLabel()
        self.files_label = QtGui.QLineEdit()
        self.default_label = QtGui.QLabel()
        self.prog_label.setReadOnly(True)
        self.files_label.setReadOnly(True)
        self.message_label.setText("Which files would you like to run your analysis on?")
        self.default_label.setText("Check to use default parameter values:")
        self.files_label.setText("")

        self.defaultButton=QtGui.QCheckBox(self)
        self.defaultButton.setChecked(True)
        
        self.progButton=QtGui.QPushButton("Select Program", self)
        self.methodButton=QtGui.QPushButton("select\ninput method", self)
        self.folderButton=QtGui.QPushButton("select\nfolder", self)
        self.runButton=QtGui.QPushButton("Run", self)

        self.progButton.clicked.connect(self.selectProgram)
        self.methodButton.pressed.connect(self.selectmethod)
        self.folderButton.pressed.connect(self.selectfolder)
        self.runButton.pressed.connect(self.startAutomation)

        self.mainLayout.addWidget(self.progButton,0,0)
        self.mainLayout.addWidget(self.prog_label,1,0)
        self.mainLayout.addWidget(self.message_label,2,0)
        self.mainLayout.addWidget(self.methodButton,3,0)
        self.mainLayout.addWidget(self.default_label,4,0)
        self.mainLayout.addWidget(self.defaultButton,4,1)
        self.mainLayout.addWidget(self.folderButton,5,0)
        self.mainLayout.addWidget(self.files_label,6,0)
        self.mainLayout.addWidget(self.runButton,7,0)

        # hide the buttons -- we haven't selected a method nor do we have files
        if self.dbdatasource:
            self.folderButton.hide()
        self.runButton.hide()

        self.show()     

    """ initializes datamembers related to the database """
    def initDB(self):
        
        self.dbdatasource = True

    """ sets either the database connection or says that we're doing manual selection """    
    def methodSetter(self, folderpath = None):
        
        if folderpath is None:
            self.dbdatasource_temp=userinputcaller(self.parent, inputs=[('DBsource?', bool, '1')], title='Change to 0 to read for local harddrive.')
            # if we didn't select a method and clicked exit instead - exit the process by returning 0
            if not self.dbdatasource_temp:
                return 0
            self.dbdatasource = self.dbdatasource_temp[0]
            if self.dbdatasource:
                self.dbc=None
        else:
            self.dbdatasource=0
         
        self.plate_id=None
        self.selectexids=None

        return 1

    def filePathDecider(self, folderpath=None):
        
        if folderpath is None:
            self.folderpath=None
            self.selectfolder()
        else:
            self.folderpath=folderpath

    """ creates  a new database conection """
    def createdbsession(self):
        
        ans=userinputcaller(self.parent, inputs=[('user:', str, ''), ('password:', str, '')], title='Enter database credentials', cancelallowed=True)
        # if we fail
        if ans is None:
            return 0
        try:
            self.dbc=mysql_dbcommlib.dbcomm(user=ans[0].strip(), password=ans[1].strip(),db='hte_echemdrop_proto')
            return 1
        except:
            idialog=messageDialog(self.parent, 'database credentials appear incorrect')
            idialog.exec_()
            return 0
            
    def selectmethod(self,folderpath=None):
        
        self.files_label.setText("")
        # we didn't select a method, so we return to the main gui
        if not self.methodSetter(folderpath):
            return

        # show the folder button since we decided to manually select files
        if not self.dbdatasource:
            self.folderButton.show()
        else:
            self.folderButton.hide()
            
        # get the paths for the files of interest
        self.filePathDecider(folderpath)


    def startAutomation(self):
        if self.paths:
            if self.prevVersion:
                xmlFiles = path_helpers.getFolderFiles(XML_DIR,'.xml')
                
            else:
                xmlFiles = []
            if self.progModule:
                self.automator = fomautomator.FOMAutomator(self.paths, xmlFiles,
                                                           self.versionName,
                                                           self.prevVersion,
                                                           self.progModule,
                                                           self.updateModule,
                                                           self.exptypes,XML_DIR,RAW_DATA_PATH)

                
                params = self.getParams(default=self.defaultButton.isChecked())
                if not params:
                    return 1
                funcNames, paramsList = params
                self.automator.setParams(funcNames, paramsList)
                self.automator.runParallel()

                                 
    def selectfolder(self, plate_id=None, selectexids=None, folder=None):
        
        # hide the run, we're in process of selecting files.
        self.runButton.hide()

        # resetting some things
        self.paths = []
        
        if self.dbdatasource:
            # since we're doing the database, hide some buttons
            self.folderButton.hide()
            if not self.dbc is None:
                print "closing old session"
                self.dbc.close()
                self.message_label.setText("")
                self.files_label.setText("")

            if not self.createdbsession():
                return 0
            
            if plate_id is None:
                ans=userinputcaller(self.parent, inputs=[('plate ID:', int, '')], title='Enter plate ID for analysis', cancelallowed=True)
                if ans is None:
                    return 0
                self.plate_id=ans[0]
            else:
                self.plate_id=plate_id

            fields=['id', 'sample_no','created_at', 'experiment_no', 'technique_name', 'dc_data__t_v_a_c_i']
            self.dbrecarrd=self.dbc.getarrd_scalarfields('plate_id', self.plate_id, fields, valcvtcstr='%d')
            if len(self.dbrecarrd['id'])==0:
                print 'NO DB RECORDS FOUND FOR PLATE ', self.plate_id
                return
            if selectexids is None:
                self.userselectdbinds()
                
            else:
                self.selectexids=selectexids
            inds=numpy.concatenate([numpy.where(self.dbrecarrd['experiment_no']==exid)[0] for exid in self.selectexids])
            for k, v in self.dbrecarrd.iteritems():
                self.dbrecarrd[k]=v[inds]     

        else:
            if folder is None:
                self.folderpath=mygetdir(self, markstr='containing echem data .txt for single plate')
            else:
                self.folderpath=folder
            # since we're not doing database and we already  took some files, we can show some buttons again
            self.folderButton.show()
        try:
            thepaths = self.getPathInfo()
        except:
            return 0
        self.message_label.setText("If you wish to select another folder, please use the button below")
        plateExperiment = "Plate " + str(self.plate_id) + " Experiments " + str(self.selectexids)
        self.files_label.setText(str(self.folderpath or plateExperiment))
        
        if thepaths:
            self.paths = thepaths
            # we have some things to run, so we can show the button
            if self.progModule:
                self.runButton.show()
        return 1

    """ gets the path info and returns them as a list """
    def getPathInfo(self, ext='.txt'):
        
        if self.dbdatasource:
            fns = self.dbrecarrd['dc_data__t_v_a_c_i']
            pathstoread_temp=[os.path.join(os.path.join('J:/hte_echemdrop_proto/data','%d' %self.plate_id), fn) for fn in fns]
            pathstoread = [os.path.normpath(path) for path in pathstoread_temp]
        else:
            pathstoread = path_helpers.getFolderFiles(self.folderpath,ext)

        return pathstoread
    
    def userselectdbinds(self):
        
        t=self.dbrecarrd['created_at']
        ex=self.dbrecarrd['experiment_no']
        tn=self.dbrecarrd['technique_name']
        
        exset=sorted(list(set(ex)))
        ex_trange_techl=[(exv, numpy.sort(t[ex==exv])[[0,-1]], list(set(tn[[ex==exv]]))) for exv in exset]
        idialog=selectdbsessionsDialog(self, ex_trange_techl=ex_trange_techl)
        idialog.exec_()
        exsetinds=idialog.selectinds
        self.selectexids=[exset[i] for i in exsetinds]
        exptypelist = [ex_trange_techl[i][2] for i in exsetinds]
        self.exptypes = []
        for tech in itertools.chain(*exptypelist):
            techname = re.sub('\d+', '', tech).rstrip()
            if techname not in self.exptypes:
                self.exptypes.append(techname)
        print self.exptypes

    def selectProgram(self):
        
        self.programDialog = QtGui.QFileDialog(self,
                                               caption = "Select a version folder containing data analysis scripts",
                                               directory = FUNC_DIR)
        
        self.programDialog.setFileMode(QtGui.QFileDialog.Directory)
        # if user clicks 'Choose'
        if self.programDialog.exec_():
            # list of QStrings (only one folder is allowed to be selected)
            dirList = self.programDialog.selectedFiles()
            targetDir = str(dirList[0])
            self.prog_label.setText(targetDir)
            # check targetDir for the target module first
            sys.path.insert(1, targetDir)
            pyFiles = filter(lambda f: f.endswith('.py'), os.listdir(targetDir))
            self.progModule = [os.path.splitext(mod)[0] for mod in pyFiles if
                               mod == MOD_NAME+'.py'][0]
            try:
                self.updateModule = [os.path.splitext(mod)[0] for mod in pyFiles if
                                     mod == UPDATE_MOD_NAME+'.py'][0]
            except IndexError:
                # no previous version
                pass
            self.versionName = os.path.basename(targetDir)
            print 'current version:', self.versionName
            funcDir = os.listdir(FUNC_DIR)
            funcDir.sort()
            verIndex = funcDir.index(self.versionName)
            if verIndex > 0:
                self.prevVersion = funcDir[verIndex-1]
            else:
                self.prevVersion = ''
            print 'previous version:', self.prevVersion

        if self.paths:
            self.runButton.show()

    """ gets the parameter input from the user or returns the default set """
    def getParams(self,default=False):
        
        params = self.automator.requestParams(default)

        # if we're using the default that parameters are in the correct format and ready to go
        if default:
            return params

        # since we're not using the default, we must get the user to give us some values
        funcs_names = [func[0] for func in params for num in range(len(func[1]))]
        funcs_params = [pname for func in params for (pname,ptype,pval) in func[1]]
        funcs_ans = []
        
        for func in params:
            ans=userinputcaller(self.parent, inputs=func[1], title='Enter Values for ' + str(func[0]), cancelallowed=True)
            if ans == None:
                return None
            funcs_ans += ans

        return funcs_names,[list(a) for a in zip(funcs_params,funcs_ans)]

    
################################################################################
######################### selectdbsessionsDialog class #########################
################################################################################
           
class selectdbsessionsDialog(QtGui.QDialog):
    
    def __init__(self, parent, ex_trange_techl, maxsessions=15, title='Select DB experiment sessions to analyze'):
        
        super(selectdbsessionsDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.mainLayout=QtGui.QVBoxLayout()
        
        self.cblist=[]
        self.cbinds=[]
        for count,  (ex, (t0, t1), techl) in enumerate(ex_trange_techl[:maxsessions]):
            cb=QtGui.QCheckBox()
            cb.setText('exp %d: %s to %s, %s' %(ex, str(t0), str(t1), ','.join(techl)))
            cb.setChecked(False)
            self.mainLayout.addWidget(cb)
            self.cblist+=[cb]
            self.cbinds+=[[count]]
        if len(ex_trange_techl)>maxsessions:
            cb=QtGui.QCheckBox()
            ex, (t0, t1), techl=ex_trange_techl[maxsessions]
            ex2, (t02, t12), techl2=ex_trange_techl[-1]
            techl=list(set(techl+techl2))
            cb.setText('exp %d-%d: %s to %s, %s' %(ex, ex2, str(t0), str(t12), ','.join(techl)))
            cb.setChecked(True)
            self.mainLayout.addWidget(cb)
            self.cblist+=[cb]
            self.cbinds+=[range(maxsessions, len(ex_trange_techl))]
        cb.setChecked(True)
        
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(520, 195, 160, 26))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.ExitRoutine)
        
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        QtCore.QMetaObject.connectSlotsByName(self)
        
    def ExitRoutine(self):
        
        self.selectinds=[]
        for cb, l in zip(self.cblist, self.cbinds):
            if cb.isChecked():
                self.selectinds+=l
                
    
################################################################################
########################## userinputDialog class ###############################
################################################################################
                
""" a class that helps us create QDialog for user input """
class userinputDialog(QtGui.QDialog):
    
    def __init__(self, parent, inputs=[('testnumber', int, '')], title='Enter values'):
        
        super(userinputDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.mainLayout= QtGui.QGridLayout()
        self.parent=parent
        self.inputs=inputs
        self.lelist=[]

        numInputs = len(self.inputs)
        row = 0
        
        for i, tup in enumerate(self.inputs):
            widthNum = 4
            col = i%widthNum
            lab=QtGui.QLabel()
            lab.setText(tup[0])
            le=QtGui.QLineEdit()
            if len(tup)>2:
                le.setText(str(tup[2]))
            self.lelist+=[le]
            if col==0:
                row+=2
            self.mainLayout.addWidget(lab, row, col, 1, 1)
            self.mainLayout.addWidget(le, row+1, col, 1, 1)
        # Space from the button    
        row+=2
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(520, 195, 160, 26))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.ExitRoutine)

        self.mainLayout.addWidget(self.buttonBox, row, 0, len(inputs), 1)
        self.setLayout(self.mainLayout)
    
        QtCore.QMetaObject.connectSlotsByName(self)
        
        self.problem=False
        self.ok=False

    def ExitRoutine(self):
        
        self.ok=True
        self.problem=False
        self.ans=[]
        self.inputstrlist=[str(le.text()).strip() for le in self.lelist]
        for s, tup in zip(self.inputstrlist, self.inputs):
            try:
                self.ans+=[myevaluator(s,tup[1])]
            except:
                self.problem=True
                break
        if self.problem:
            idialog=messageDialog(self, 'problem with conversion of ' + tup[0])
            idialog.exec_()


################################################################################
############################ messageDialog class ###############################
################################################################################

""" class for delivering simple messages through a QDialog box"""            
class messageDialog(QtGui.QDialog):
    
    def __init__(self, parent=None, title=''):
        
        super(messageDialog, self).__init__(parent)
        
        self.setWindowTitle(title)
        self.mainLayout=QtGui.QGridLayout()
  
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setGeometry(QtCore.QRect(520, 195, 160, 26))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.ExitRoutine)
        self.buttonBox.rejected.connect(self.reject)
        
        self.mainLayout.addWidget(self.buttonBox, 0, 0)
        self.setLayout(self.mainLayout)
        
    def ExitRoutine(self):
        
        return

    
################################################################################
########################## Helper Functions ####################################
################################################################################
            
""" assist in creating dialog boxes for the user to input information we need """
def userinputcaller(parent, inputs=[('testnumber', int)], title='Enter values',  cancelallowed=True):
    
    problem=True
    while problem:
        idialog=userinputDialog(parent, inputs, title)
        idialog.exec_()
        problem=idialog.problem
        if not idialog.ok and cancelallowed:
            return None
        inputs=[(tup[0], tup[1], s) for tup, s  in zip(inputs, idialog.inputstrlist)]

    return idialog.ans

""" helps select a folder directory """
def mygetdir(parent=None, xpath="%s" % os.getcwd(),markstr='' ):
    
    if parent is None:
        xapp = QtGui.QApplication(sys.argv)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
        xparent = QWidget()
        returnfn = unicode(QtGui.QFileDialog.getExistingDirectory(xparent,''.join(['Select directory:', markstr]), xpath))
        xparent.destroy()
        xapp.quit()
        return returnfn
    return unicode(QtGui.QFileDialog.getExistingDirectory(parent,''.join(['Select directory:', markstr]), xpath))
                    
""" evaluates c based on the type it is """
def myevaluator(c, theType):
    
    if c=='None':
        c=None
    elif c=='nan' or c=='NaN':
        c=numpy.nan
    else:
        # does this in case we do c = 0 and theType = bool
        temp=c.lstrip('0')
        if (temp=='' or temp=='.') and '0' in c:
            c=0
        c = theType(c)
    return c

if __name__ == '__main__':
    mainapp=QtGui.QApplication(sys.argv)
    mm = echemvisDialog()
    sys.exit(mainapp.exec_())
