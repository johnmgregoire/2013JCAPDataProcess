# Allison Schubauer and Daisy Hernandez
# Created: 6/26/2013
# Last Updated: 7/23/2013
# For JCAP

"""
    runs functions to produce figures of merit automatically, and
    replaces dictionaries of data produced by old versions with
    updated data
"""

import sys, os, argparse
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

FUNC_DIR = os.path.normpath(os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisFunctions"))
XML_DIR = os.path.normpath(os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisXML"))

class FOMAutomator(object):
    
    """ initializes the automator with all necessary information """
    def __init__(self, rawDataFiles, xmlFiles, versionName, prevVersion,funcModule,
                 updateModule, expTypes, outDir, rawDataDir,errorNum,jobname):
        # initializing all the basic info
        self.version = versionName
        self.lastVersion = prevVersion
        # the os.path.insert in either the gui or in the terminal argument
        # reigion is what makes sure we select the right function Module
        self.funcMod = __import__(funcModule)
        self.modname = funcModule
        self.updatemod = updateModule
        self.expTypes = expTypes
        self.outDir = outDir
        self.rawDataDir = rawDataDir
        self.errorNum = errorNum
        self.jobname = jobname
        self.files = []

        # setting up everything having to do with saving the XML files
        for rdpath in rawDataFiles:
            xmlpath = path_helpers.giveAltPathAndExt(outDir,rdpath,'.xml')
            if xmlpath in xmlFiles:
                self.files.append((rdpath, xmlpath))
            else:
                self.files.append((rdpath, ''))

    """ starts running the jobs in parallel and initializes logging """
    def runParallel(self):
        statusFileName = path_helpers.createPathWExtention(self.outDir,self.jobname,".run")
        
        # setting up the manager and things required to log due to multiprocessing
        pmanager = Manager()
        loggingQueue = pmanager.Queue()
        processPool = Pool()
        fileHandler = logging.FileHandler(statusFileName)
        logFormat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(logFormat)
        fileLogger = QueueListener(loggingQueue, fileHandler)
        fileLogger.start()
        
        # the jobs to process each of the files
        jobs = [(loggingQueue, filename, xmlpath, self.version,
                 self.lastVersion, self.modname, self.updatemod,
                 self.params, self.funcDicts, self.outDir, self.rawDataDir)
                for (filename, xmlpath) in self.files]
        processPool.map(makeFileRunner, jobs)
        print "The filelogger has logged", fileLogger.errorCount

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        processHandler = QueueHandler(loggingQueue)
        root.addHandler(processHandler)

        if fileLogger.errorCount > self.errorNum:
            root.error("The ")
        
        processPool.close()
        processPool.join()
        fileLogger.stop()
        fileHandler.close()
        """try:
            if numberOfErrors > self.errorNum:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname,".error"))
            else:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname,".done"))
        except:
            if numberOfErrors > self.errorNum:
                pass
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname+timeStamp,".error"))
            else:
                pass
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname+timeStamp,".done"))
        """

    """ runs the files in order on a single process and logs errors """
    def runSequentially(self):
        # setting up everything needed for logging the errors
        loggingQueue = queue.Queue()
        statusFileName = path_helpers.createPathWExtention(self.outDir,self.jobname,".run")
        fileHandler = logging.FileHandler(statusFileName)
        logFormat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fileLogger = QueueListener(loggingQueue, fileHandler)
        fileLogger.start()

        # setting up the actual logger
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        processHandler = QueueHandler(loggingQueue)
        root.addHandler(processHandler)

        numberOfFiles = len(self.files)
        bTime= time.time()
        
        # The file processing occurs here
        logQueue = None
        for i, (filename, xmlpath) in enumerate(self.files):
            if fileLogger.errorCount > self.errorNum:
                root.info("The job encountered %d errors and the max number of them allowed is %d" %(fileLogger.errorCount,self.errorNum))
                break
            
            try:
                root.info("Processing file %s %d/%d" %(filename,i+1,numberOfFiles))
                exitcode = filerunner.FileRunner(logQueue,filename,xmlpath, self.version,
                                                 self.lastVersion, self.modname, self.updatemod,
                                                 self.params, self.funcDicts,self.outDir,
                                                 self.rawDataDir)
            except Exception as someException:
                # root.exception will log an ERROR with printed traceback;
                # root.error will log an ERROR without traceback
                root.exception(someException)
                exitcode = -1

        eTime= time.time()
        root.info("Processed for %f seconds" %(eTime-bTime,))
        timeStamp = time.strftime('%Y%m%d%H%M%S',time.gmtime())

        # cleaning up what was left of the loggers
        # closing the fileHandler is important or else we cannot rename the file
        root.removeHandler(processHandler)
        fileLogger.stop()      
        fileHandler.close()

        # the renaming of the run file based on the way the file processing ended
        if fileLogger.errorCount > self.errorNum:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname,".error"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname+timeStamp,".error"))
        else:
            try:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname,".done"))
            except:
                os.rename(statusFileName, path_helpers.createPathWExtention(self.outDir,self.jobname+timeStamp,".done"))

        
    """ returns a dicitonary with all the parameters and batch variables in """
    def processFuncs(self):
        self.params = {}
        self.funcDicts = {}
        self.allFuncs = []

        # if we have the type of experiment, we can just get the specific functions
        if self.expTypes:         
            for tech in self.expTypes:
                techDict = self.funcMod.EXPERIMENT_FUNCTIONS.get(tech)
                if techDict:
                    [self.allFuncs.append(func) for func in techDict
                     if func not in self.allFuncs]

        # if not we just get them all                     
        else:
            self.allFuncs = [f[0] for f in getmembers(self.funcMod, isfunction)]
                        
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
                else:
                    self.params[fname+'_'+arg] = val
                    funcdict['params'].append(arg)
                    funcdict['#'+arg] = val
            self.funcDicts[fname] = funcdict
        return self.funcDicts

    """ changes the parameter value in the function dictionary """
    def setParams(self, funcNames, paramsList):
        for fname, params in zip(funcNames, paramsList):
            fdict = self.funcDicts[fname]
            param,val = params
            fdict['#'+param] = val
            self.params[fname+'_'+param] = val

    """ returns a list of the parameters if the default is false, else it returns
        the functions and values that can be passed to setParams """
    def requestParams(self,default=True):
        funcNames = (self.processFuncs().keys())
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

class ErrorFilter(logging.Filter):
    def __init__(self, name=''):
        super(ErrorFilter, self).__init__(name)

    def filter(self, record):
        return record.levelno == logging.ERROR

def makeFileRunner(args):
    queue = args[0]
    filename = os.path.splitext(os.path.split(args[1])[1])[0]
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    processHandler = QueueHandler(queue)
    root.addHandler(processHandler)
    try:
        exitcode = filerunner.FileRunner(*args)
        root.info('File %s completed' %filename)
    except Exception as someException:
        # root.exception will log an ERROR with printed traceback;
        #   root.error will log an ERROR without traceback
        root.error('Exception raised in file %s:\n' %filename +repr(someException))
        #root.exception(someException)
        exitcode = -1
    finally:
        root.removeHandler(processHandler)
        return exitcode
    

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-I','--inputfolder', type=str, help="The input folder", nargs=1, required=True)
    parser.add_argument('-i', '--inputfile',  type=str, help="The input file",  nargs=1)
    parser.add_argument('-f', '--fileofinputs', type=str, help="File containing input files", nargs=1)
    parser.add_argument('-J','--jobname', type=str, help="The job_name", nargs=1)
    parser.add_argument('-O', '--outputfolder', type=str, help="The output folder", nargs=1, required=True)
    parser.add_argument('-X', '--errornum', type=int, help="The maximum number of errors", nargs=1)
    args = parser.parse_args(argv)

    paths = []
    outputDir = None
    jobname = ""
    max_errors = 1

    if not (args.inputfolder or args.inputfile or args.fileofinputs):
        parser.error('Cannot proceed further as no form of input was specified Plesase use either -I,-i, or -f, please.')
        
    if args.inputfolder:
        paths += path_helpers.getFolderFiles(args.inputfolder[0], '.txt')

    if args.inputfile:
        paths += args.inputfolder

    if args.fileofinputs:
        try:
            with open(args.fileofinputs[0], 'r') as fileWithInputFiles:
               paths += fileWithInputFiles.read().splitlines()
        except:
            #TODO: Putt a message to the logger
            pass
    if args.jobname:
        jobname=args.jobname[0]

    if args.errornum:
        max_errors = args.errornum[0]
        
    if args.outputfolder:
        outputDir = args.outputfolder[0]
    else:
        return


    xmlFiles = path_helpers.getFolderFiles(outputDir,'.xml')
    versionName, prevVersion = fomautomator_helpers.getVersions(FUNC_DIR)
    updateModule = "fomfunctions_update"
    sys.path.insert(1, os.path.join(FUNC_DIR,versionName))
    progModule = "fomfunctions"
    exptypes = []
    xmlPath = XML_DIR
    rawPath = RAW_DATA_PATH

    if paths:
        automator = FOMAutomator(paths, xmlFiles,versionName,prevVersion,progModule,updateModule,exptypes, xmlPath,rawPath,max_errors,jobname)
        funcNames, paramsList = automator.requestParams(default=True)
        automator.setParams(funcNames, paramsList)
        automator.runParallel()
        #automator.runSequentially()
        

if __name__ == "__main__":
    main(sys.argv[1:])

# python fomautomator.py -I "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\5 File" -O "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\AutoAnalysisXML" -J "jobnametest"
