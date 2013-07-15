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

FUNC_DIR = os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisFunctions")
XML_DIR = os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisXML")

class FOMAutomator(object):
    def __init__(self, rawDataFiles, xmlFiles, versionName, prevVersion,
                 funcModule, expTypes):
        # initializing all the basic info
        self.version = versionName
        self.lastVersion = prevVersion
        self.funcMod = __import__(funcModule)
        self.modname = funcModule
        self.expTypes = expTypes
        self.files = []

        # setting up everything haveing to do with saving the XML files
        for rdpath in rawDataFiles:
            xmlpath = path_helpers.giveAltPathAndExt(XML_DIR,rdpath,'.xml')
            if xmlpath in xmlFiles:
                self.files.append((rdpath, xmlpath))
            else:
                self.files.append((rdpath, ''))

    def runParallel(self):
        #self.processFuncs() #called by GUI
        #self.requestParams() #handled separately by GUI
        pmanager = Manager()
        loggingQueue = pmanager.Queue()
        processPool = Pool()
        handler = logging.FileHandler('test.log')
        logFormat = logging.Formatter('%(message)s')
        handler.setFormatter(logFormat)
        fileLogger = QueueListener(loggingQueue, handler)
        fileLogger.start()
        jobs = [(loggingQueue, filename, xmlpath, self.version,
                 self.lastVersion, self.modname, self.params, self.funcDicts)
                for (filename, xmlpath) in self.files]
        processPool.map(makeFileRunner, jobs)
        processPool.close()
        processPool.join()
        fileLogger.stop()

    def processFuncs(self):
        self.params = {}
        self.funcDicts = {}
        self.allFuncs = []
        if self.expTypes:
            for tech in self.expTypes:
                techDict = self.funcMod.validFuncs.get(tech)
                if techDict:
                    for func in techDict:
                        if func not in self.allFuncs:
                            self.allFuncs.append(func)
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

    def setParams(self, funcNames, paramsList):
        for fname, params in zip(funcNames, paramsList):
            fdict = self.funcDicts[fname]
            param,val = params
            fdict['#'+param] = val
            self.params[fname+'_'+param] = val

##    def requestParams(self):
##        for fname in self.funcDicts.keys():
##            fdict = self.funcDicts[fname]
##            if fdict.get('params'):
##                usedefault = distutils.util.strtobool(raw_input("Use default parameters for "+fname+"? "))
##                # uncomment ^ this line to take parameters from user
##             x   #usedefault = True #THIS IS FOR TESTING ONLY
##                if not usedefault:
##                    for param in fdict.get('params'):
##                        newval = raw_input(param+": ")
##                        self.params[fname+'_'+param] = attemptnumericconversion(newval)
##                        fdict['#'+param] = attemptnumericconversion(newval)

    def accessDict(self, fname, varset, argname):
        fdict = self.funcDicts.get(fname)
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


def makeFileRunner(args):
    return FileRunner(*args)

class FileRunner(object):
    def __init__(self, queue, expfile, xmlpath, version, lastversion, modname, newparams, funcdicts):
        self.txtfile = expfile
        self.expfilename = os.path.splitext(os.path.split(self.txtfile)[1])[0]
        self.version = version
        self.modname = modname
        self.fdicts = funcdicts
        oldversion = 0
        if lastversion:
            oldversion, self.FOMs, self.interData, self.params = xmltranslator.getDataFromXML(xmlpath)
            #print "xml read"
        if oldversion != lastversion:
            #print "from scratch"
            self.FOMs, self.interData, self.params = {}, {}, {}
        for param in newparams:
            self.params[param] = newparams[param]
        # look for raw data dictionary before creating one from the text file
        try:
            rawdatafile = os.path.join(RAW_DATA_PATH,
                                       [fname for fname in os.listdir(RAW_DATA_PATH)
                                        if self.expfilename in fname][0])
        except IndexError:
            #print "brand new file"
            rawdatafile = readechemtxt(self.txtfile)            
        with open(rawdatafile) as rawdata:
            self.rawData = pickle.load(rawdata)
##        self.run()
##
##    def run(self):
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
        savepath = os.path.join(XML_DIR, self.expfilename+'.xml')
        dataTup = (self.FOMs, self.interData, self.params)
        xmltranslator.toXML(savepath, self.version, dataTup)

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-I','--inputfolder', type=str, help="The input folder", nargs=1)
    parser.add_argument('-i', '--inputfile',  type=str, help="The input file",  nargs=1)
    parser.add_argument('-f', '--askabout', type=str, help="File containing input files", nargs=1)
    parser.add_argument('-J','--jobname', type=str, help="The job_name", nargs=1)
    parser.add_argument('-O', '--outputfolder', type=str, help="The output folder", nargs=1)
    parser.add_argument('-X', '--errornum', type=int, help="The maximum number of errors", nargs=1)
    args = vars(parser.parse_args(argv))

    if args["inputfolder"]:
        print path_helpers.getFolderFiles(args["inputfolder"][0], '.txt')

if __name__ == "__main__":
    main(sys.argv[1:])
