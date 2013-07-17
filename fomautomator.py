# Allison Schubauer and Daisy Hernandez
# Created: 6/26/2013
# Last Updated: 7/15/2013
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
from rawdataparser import *
from qhtest import *
import jsontranslator
import xmltranslator
import importlib
import distutils.util
import itertools
import path_helpers
import fomautomator_helpers

FUNC_DIR = os.path.normpath(os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisFunctions"))
XML_DIR = os.path.normpath(os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisXML"))

class FOMAutomator(object):
    """ initializes the automator with all necessary information """
    def __init__(self, rawDataFiles, xmlFiles, versionName, prevVersion,
                 funcModule, expTypes, outDir, rawDataDir):
        
        # initializing all the basic info
        self.version = versionName
        self.lastVersion = prevVersion
        self.funcMod = __import__(funcModule)
        self.modname = funcModule
        self.expTypes = expTypes
        self.outDir = outDir
        self.rawDataDir = rawDataDir
        self.files = []

        # setting up everything having to do with saving the XML files
        for rdpath in rawDataFiles:
            xmlpath = path_helpers.giveAltPathAndExt(outDir,rdpath,'.xml')
            if xmlpath in xmlFiles:
                self.files.append((rdpath, xmlpath))
            else:
                self.files.append((rdpath, ''))

    """ starts running the jobs in parrallel and initilizes logging """
    def runParallel(self):     
        # setting up the manager and things required to log due to multiprocessing
        pmanager = Manager()
        loggingQueue = pmanager.Queue()
        processPool = Pool()
        handler = logging.FileHandler('test.log')
        logFormat = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(logFormat)
        fileLogger = QueueListener(loggingQueue, handler)
        fileLogger.start()
        
        # the jobs to process each of the files
        jobs = [(loggingQueue, filename, xmlpath, self.version,
                 self.lastVersion, self.modname, self.params, self.funcDicts, self.outDir, self.rawDataDir)
                for (filename, xmlpath) in self.files]
        processPool.map(makeFileRunner, jobs)
        processPool.close()
        processPool.join()
        fileLogger.stop()

    def processFuncs(self):
        self.params = {}
        self.funcDicts = {}
        self.allFuncs = []
        
        # if we have the type of experiment, we can just get the specific functions
        if self.expTypes:
            for tech in self.expTypes:
                techDict = self.funcMod.validFuncs.get(tech)
                if techDict:
                    for func in techDict:
                        if func not in self.allFuncs:
                            self.allFuncs.append(func)
        # if not we just get them all                     
        else:
            self.allFuncs = [f[0] for f in getmembers(self.funcMod, isfunction)]
                        
        for fname in self.allFuncs:
            funcObj = [f[1] for f in getmembers(self.funcMod, isfunction) if
                       f[0] == fname][0]
            funcdict = {'batchvars': [], 'params': []}
            dictargs = funcObj.func_code.co_argcount - len(funcObj.func_defaults)
            funcdict['numdictargs'] = dictargs
            arglist = zip(funcObj.func_code.co_varnames[dictargs:],
                          funcObj.func_defaults) 
            
            for arg, val in arglist:
                if isinstance(val, list):
                    funcdict['batchvars'].append(arg)
                    funcdict['~'+arg] = val
                #elif (val in RAW_DATA) or (val in INTER_DATA):
                # we can't check this ^ if we process function before looking at data
                # so intead just check if it's a string and assume it's data
                #   (new version tester should verify this somehow)
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

def makeFileRunner(args):
    return FileRunner(*args)

class FileRunner(object):
    def __init__(self, queue, expfile, xmlpath, version, lastversion, modname, newparams, funcdicts,
                 outDir, rawDataDir):
        self.txtfile = expfile
        self.expfilename = os.path.splitext(os.path.split(self.txtfile)[1])[0]
        self.version = version
        self.modname = modname
        self.outDir = outDir
        self.rawDataDir = rawDataDir
        self.fdicts = funcdicts
        self.FOMs, self.interData, self.params = {}, {}, {}     
        if lastversion and xmlpath:
            oldversion, self.FOMs, self.interData, self.params = xmltranslator.getDataFromXML(xmlpath)
        for param in newparams:
            self.params[param] = newparams[param]
        # look for raw data dictionary before creating one from the text file
        try:
            rawdatafile = os.path.join(self.rawDataDir,
                                       [fname for fname in os.listdir(self.rawDataDir)
                                        if self.expfilename in fname][0])
        except IndexError:
            rawdatafile = readechemtxt(self.txtfile)
        try: 
            with open(rawdatafile) as rawdata:
                self.rawData = pickle.load(rawdata)
        except:
            return

        funcMod = __import__(self.modname)
        allFuncs = [f[1] for f in getmembers(funcMod, isfunction)]
        validDictArgs = [self.rawData, self.interData]
        expType = self.rawData.get('BLTechniqueName')
        print 'expType:', expType
        targetFOMs = funcMod.validFuncs.get(expType)
        if not targetFOMs:
            print self.txtfile
            return
        fomFuncs = [func for func in allFuncs if func.func_name in targetFOMs]
        for funcToRun in fomFuncs:
            fname = funcToRun.func_name
            fdict = self.fdicts[fname]
            fdictargs = validDictArgs[:fdict['numdictargs']]
            allvarsets = [fdict.get('~'+batch) for batch in fdict.get('batchvars')]
            commonvars = lambda vartup, varlist: [var for var in varlist if
                                                  var in vartup]
            # requires list of lists - I'm not sure if I like this (it's silly for functions
            #   with one batch variable)
            for varset in [commonvars(vartup, varlist) for vartup in
                           itertools.product(*allvarsets) for varlist in
                           targetFOMs[fname]]:
                # this is to make up for the fact that commonvars returns empty lists and
                #   single-argument lists for two or more batch variables - probably shouldn't
                #   be a permanent solution
                if len(varset) == len(fdict.get('batchvars')):
                    fom = funcToRun(**dict(zip(funcToRun.func_code.co_varnames[:funcToRun.func_code.co_argcount],
                                                fdictargs+[self.accessDict(fname, varset, argname) for argname
                                                in funcToRun.func_code.co_varnames[fdict['numdictargs']:funcToRun.func_code.co_argcount]])))
                    self.FOMs[('_').join(map(str, varset))+'_'+fname] = fom
        # temporary function to monitor program's output
        self.saveXML()
        processHandler = QueueHandler(queue)  
        root = logging.getLogger()
        root.setLevel('INFO')
        root.addHandler(processHandler)
        root.info('File %s completed' %self.expfilename)
        return

    def accessDict(self, fname, varset, argname):
        fdict = self.fdicts.get(fname)
        try:
            # parameter
            return self.params[fname+'_'+argname]
        except KeyError:
            if argname in fdict['batchvars']:
                # retrieve current variable in batch
                datavar = [var for var in varset if var in fdict['~'+argname]][0]
                return datavar
            elif (fdict[argname] in self.rawData) or (fdict[argname] in self.interData):
                # raw/intermediate data value
                return fdict[argname]
            else:
                # this error will need to be handled somehow, and this
                #   is something that should definitely be tested in
                #   the committer
                print argname, "is not a valid argument"

    def saveXML(self):
        savepath = os.path.join(self.outDir, self.expfilename+'.xml')
        dataTup = (self.FOMs, self.interData, self.params)
        xmltranslator.toXML(savepath, self.version, dataTup)

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-I','--inputfolder', type=str, help="The input folder", nargs=1, required=True)
    parser.add_argument('-i', '--inputfile',  type=str, help="The input file",  nargs=1)
    parser.add_argument('-f', '--askabout', type=str, help="File containing input files", nargs=1)
    parser.add_argument('-J','--jobname', type=str, help="The job_name", nargs=1)
    parser.add_argument('-O', '--outputfolder', type=str, help="The output folder", nargs=1, required=True)
    parser.add_argument('-X', '--errornum', type=int, help="The maximum number of errors", nargs=1)
    args = vars(parser.parse_args(argv))

    paths = []
    outputDir = None
    jobname = ""
    max_errors = 10
    
    if args["inputfolder"]:
        paths += path_helpers.getFolderFiles(args["inputfolder"][0], '.txt')
    else:
        return

    if args["inputfile"]:
        path += args["inputfolder"][0]

    if args["errornum"]:
        max_errors = args["errornum"][0]
        
    if args["outputfolder"]:
        outputDir = args["outputfolder"][0]
    else:
        return


    xmlFiles = path_helpers.getFolderFiles(outputDir,'.xml')
    versionName, prevVersion = fomautomator_helpers.getVersions(FUNC_DIR)
    versionName, prevVersion  = '0', ''
    sys.path.insert(1, os.path.join(FUNC_DIR,versionName))
    progModule = "fomfunctions"
    exptypes = []
    
    automator = FOMAutomator(paths, xmlFiles,versionName,prevVersion,progModule,exptypes,XML_DIR,RAW_DATA_PATH)
    funcNames, paramsList = automator.requestParams(default=True)
    automator.setParams(funcNames, paramsList)
    automator.runParallel()
        

if __name__ == "__main__":
    main(sys.argv[1:])

# python fomautomator.py -I "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\1 File" -O "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\AutoAnalysisXML"
