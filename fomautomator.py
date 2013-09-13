# Allison Schubauer and Daisy Hernandez
# Created: 6/26/2013
# Last Updated: 7/25/2013
# For JCAP

"""
    runs functions to produce figures of merit automatically, and
    replaces dictionaries of data produced by old versions with
    updated data
"""

import sys, os

import argparse
import cPickle as pickle
from multiprocessing import Process, Pool, Manager
from inspect import *
from rawdataparser import RAW_DATA_PATH
from qhtest import * # this also imports queue
import jsontranslator
import xmltranslator
import importlib
import distutils.util
import path_helpers
import fomautomator_helpers
import filerunner
import time
import datetime
from infodbcomm import infoDictfromDB
# the directory where the versions of the fomfunctions are
FUNC_DIR = os.path.normpath(os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisFunctions"))
MOD_NAME = 'fomfunctions'
UPDATE_MOD_NAME = 'fomfunctions_update'

""" The FOMAutomator class provides the framework for processing data files
    automatically.  Its main method, defined in fom_commandline, can be accessed
    through the command line.  Alternatively, the FOMAutomator can be started
    with the user interface in fomautomator_menu.  The automator can either
    process files in sequence on a single process or use Python's multiprocessing
    framework to process files on an optimal number of processes for your
    system (determined by Python).  Both options are available through the command
    line and user interface, but the command line defaults to running sequentially.
    In both implementations, status messages and errors are logged to a file in the
    output directory, and the FileRunner class (defined in filerunner.py) is used
    to process each individual file.
"""

class FOMAutomator(object):
    
    """ initializes the automator with all necessary information """
    def __init__(self, rawDataFiles, versionName, prevVersion,funcModule,
                 updateModule, technique_names, srcDir, dstDir, rawDataDir,errorNum,jobname):
        # initializing all the basic info
        self.version = versionName
        self.lastVersion = prevVersion
        # the os.path.insert in the gui or in main is what makes 
        # we select the correct function module
        self.funcMod = __import__(funcModule)
        self.modname = funcModule
        self.updatemod = updateModule
        self.technique_names = technique_names
        self.srcDir = srcDir
        self.dstDir = dstDir
        self.rawDataDir = rawDataDir
        # the max number of errors allowed by the user
        self.errorNum = errorNum
        self.jobname = jobname
        self.files = rawDataFiles
        self.infoDicts=infoDictfromDB(self.files) # required to have keys 'reference_Eo' and 'technique_name'

        self.processFuncs()

    """ returns a dictionary with all of the parameters and batch variables
        for the fom functions that will be run """
    def processFuncs(self):
        self.params = {}
        self.funcDicts = {}
        self.allFuncs = []

        # if we have the type of experiment, we can just get the specific functions
        if self.technique_names:         
            for tech in self.technique_names:
                techDict = self.funcMod.EXPERIMENT_FUNCTIONS.get(tech)
                if techDict:
                    [self.allFuncs.append(func) for func in techDict
                     if func not in self.allFuncs]
        # if not we just get them all                     
        else:
            self.allFuncs = [f[0] for f in getmembers(self.funcMod, isfunction)]

        # now that we have all the functions, we get all the parameters
        for fname in self.allFuncs:
            funcObj = [f[1] for f in getmembers(self.funcMod, isfunction) if
                       f[0] == fname][0]
            funcdict = {'batchvars': [], 'params': []}
            try:
                dictargs = funcObj.func_code.co_argcount - len(funcObj.func_defaults)
                funcdict['numdictargs'] = dictargs
                arglist = zip(funcObj.func_code.co_varnames[dictargs:],
                              funcObj.func_defaults)
            except TypeError: # if there are no keyword arguments
                dictargs = funcObj.func_code.co_argcount
                funcdict['numdictargs'] = dictargs
                arglist = []

            # note: we're assuming any string argument to the functions that the user wrote is data
            # for example t = 't(s)' in the function would mean t is equal to the raw data column t(s)
            for arg, val in arglist:
                if isinstance(val, list):
                    funcdict['batchvars'].append(arg)
                    funcdict['~'+arg] = val
                elif isinstance(val, str):
                    funcdict[arg] = val
## ---- VSHIFT -------------------------------------------------------   
##                elif arg == 'vshift':
##                    pass
## -------------------------------------------------------------------              
                else:
                    self.params[fname+'_'+arg] = val
                    funcdict['params'].append(arg)
                    funcdict['#'+arg] = val
            self.funcDicts[fname] = funcdict

    """ Returns a list of functions and their parameters, which can be
        changed by the user if running fomautomator_menu.  This function is
        only called by fomautomator_menu.   If 'default' is true, the default
        parameters defined in the fom functions file are used; otherwise, the
        parameters are requested from the user. """
    def requestParams(self,default=True):
        funcNames = self.funcDicts.keys()
        funcNames.sort()
        params_full = [[ fname, [(pname,type(pval),pval) for pname in self.funcDicts[fname]['params']
                     for pval in [self.funcDicts[fname]['#'+pname]]]]
                    for fname in funcNames if self.funcDicts[fname]['params'] != []]
        if not default:
            return params_full
        else:
            funcs_names = [func[0] for func in params_full for num in range(len(func[1]))]
            params_and_answers = [[pname,pval] for func in params_full for (pname,ptype,pval) in func[1]]
            return funcs_names, params_and_answers

    """ If the parameter values were changed by fomautomator_menu, save
        the changed values in the automator's parameter dictionary and
        function dictionary. """
    def setParams(self, funcNames, paramsList):
        for fname, params in zip(funcNames, paramsList):
            fdict = self.funcDicts[fname]
            param,val = params
            fdict['#'+param] = val
            self.params[fname+'_'+param] = val

    """ processes the files in parallel, logs status messages and errors """
    def runParallel(self):
        # the path to which to log - will change depending on the way
        #   processing ends and if a statusFile with the same
        #   name already exists
        statusFileName = path_helpers.createPathWExtention(self.dstDir,self.jobname,".run")

        # set up the manager and objects required for logging due to multiprocessing
        pmanager = Manager()
        # this queue takes messages from individual processes and passes them
        #   to the QueueListener
        loggingQueue = pmanager.Queue()
        processPool = Pool()
        # handler for the logging file
        fileHandler = logging.FileHandler(statusFileName)
        logFormat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(logFormat)
        # the QueueListener takes messages from the logging queue and passes
        #   them through another queue to the fileHandler (logs safely because
        #   only this main process writes to the fileHandler)
        fileLogger = QueueListener(loggingQueue, fileHandler)
        fileLogger.start()

        # keep track of when processing started
        bTime = time.time()
        
        # the jobs to process each of the files
#        jobs = [(loggingQueue, filename, self.version, self.lastVersion,
#                 self.modname, self.updatemod,self.params, self.funcDicts,
#                 self.srcDir, self.dstDir, self.rawDataDir)
#                for filename in self.files]

        jobs = [(loggingQueue, filename, self.version, self.lastVersion,
                 self.modname, self.updatemod, self.params, self.funcDicts,
                 self.srcDir, self.dstDir, self.rawDataDir, infodict['reference_Eo'], infodict['technique_name']) \
                 for (filename, infodict)
                in zip(self.files, self.infoDicts)]  
        
        processPool.map(makeFileRunner, jobs)
        # keep track of when processing ended
        eTime = time.time()
        timeStamp = time.strftime('%Y%m%d%H%M%S',time.gmtime())

        # clean up the pool
        processPool.close()
        processPool.join()

        root = logging.getLogger()
        if fileLogger.errorCount > self.errorNum:
            root.info("The job encountered %d errors and the max number of them allowed is %d" %(fileLogger.errorCount,self.errorNum))
        root.info("Processed for %s H:M:S" %(str(datetime.timedelta(seconds=eTime-bTime)),))
    
        fileLogger.stop()
        fileHandler.close()

        if fileLogger.errorCount > self.errorNum:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname,".error"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname+timeStamp,".error"))
        else:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname,".done"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname+timeStamp,".done"))
                
    """ runs the files in order on a single process and logs errors """
    def runSequentially(self):
        # set up everything needed for logging the errors
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        statusFileName = path_helpers.createPathWExtention(self.dstDir,self.jobname,".run")
        fileHandler = logging.FileHandler(statusFileName)
        logFormat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(logFormat)
        root.addHandler(fileHandler)

        numberOfFiles = len(self.files)
        numberOfErrors = 0
        bTime= time.time()
        
        # The file processing occurs here
        logQueue = None
        for i, (filename, infodict) in enumerate(zip(self.files, self.infoDicts)):       
            if numberOfErrors > self.errorNum:
                root.info("The job encountered %d errors and the max number of them allowed is %d" %(numberOfErrors,self.errorNum))
                break
            try:
                # returns 1 if file was processed and 0 if file was skipped
                exitcode = filerunner.FileRunner(logQueue,filename, self.version,
                                                 self.lastVersion, self.modname, self.updatemod,
                                                 self.params, self.funcDicts,self.srcDir,
                                                 self.dstDir, self.rawDataDir, infodict['reference_Eo'], infodict['technique_name'])

                if exitcode.exitSuccess:
                    root.info('File %s completed  %d/%d' %(os.path.basename(filename),i+1,numberOfFiles))
            except Exception as someException:
                # root.exception will log an ERROR with printed traceback;
                # root.error will log an ERROR without traceback
                # root.exception(someException)
                root.error('Exception raised in file %s:\n' %filename +repr(someException))
                numberOfErrors +=1
                exitcode = -1

        eTime= time.time()
        root.info("Processed for %s H:M:S" %(str(datetime.timedelta(seconds=eTime-bTime)),))
        timeStamp = time.strftime('%Y%m%d%H%M%S',time.gmtime())

        # closing the fileHandler is important or else we cannot rename the file
        root.removeHandler(fileHandler)
        fileHandler.close()

        # the renaming of the run file based on the way the file processing ended
        if numberOfErrors > self.errorNum:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname,".error"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname+timeStamp,".error"))
        else:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname,".done"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.dstDir,self.jobname+timeStamp,".done"))

""" This function is started in a separate process by ProcessPool.map.
    Here, a FileRunner is created and a processHandler is added temporarily
    to log status or error messages from the FileRunner.  The argument to
    makeFileRunner is the list of arguments to the FileRunner, but this function
    is only allowed a single argument because of ProcessPool.map. """
def makeFileRunner(args):
    # the multiprocessing queue
    queue = args[0]
    filename = os.path.basename(args[1])
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # a logging handler which sends messages to the multiprocessing queue
    processHandler = QueueHandler(queue)
    root.addHandler(processHandler)
    try:
        # exitSuccess is 1 if file was processed or 0 if file was too short
        exitcode = filerunner.FileRunner(*args)
        # if file was processed, write logging message
        if exitcode.exitSuccess:
            root.info('File %s completed' %filename)
    except Exception as someException:
        # root.exception will log an ERROR with printed traceback;
        # root.error will log an ERROR without traceback
        root.error('Exception raised in file %s:\n' %filename +repr(someException))
        #root.exception(someException)
        exitcode = -1
    finally:
        # remove handler for this file (because a new handler is created
        #   for every file)
        root.removeHandler(processHandler)
        return exitcode
