# Allison Schubauer and Daisy Hernandez
# 6/26/2013
# framework to run all functions in fomfunctions file automatically

import sys
import cPickle as pickle
from multiprocessing import Process, Pool
from inspect import *
from rawdataparser import *
import jsontranslator
import xmltranslator
import importlib
import distutils.util
import itertools

class FOMAutomator(object):
    def __init__(self, rawDataFiles, funcModule):
        self.funcMod = __import__(funcModule)
        self.modname = funcModule
        self.allFuncs = [f[1] for f in getmembers(self.funcMod, isfunction)]
        self.files = rawDataFiles

    def runParallel(self):
        self.processFuncs()
        self.requestParams()
        processPool = Pool()
        jobs = [(filename, self.modname, self.params, self.funcDicts) for filename in self.files]
        processPool.map(makeFileRunner, jobs)
        processPool.close()
        processPool.join()

    def runSequentially(self):
        # user-input params for each function are the same for all files in this session
        self.processFuncs()
        self.requestParams()
        # this is the sequential part
        for expfile in self.files:
            # intermediate data and figures of merit are different for every file
            self.interData = {}
            self.FOMs = {}
            rawdatafile = readechemtxt(expfile)
            with open(rawdatafile) as rawdata:
                self.rawData = pickle.load(rawdata)
            validDictArgs = [self.rawData, self.interData]
            expType = self.rawData.get('BLTechniqueName')
            print 'expType:', expType
            targetFOMs = self.funcMod.validFuncs.get(expType)
            if not targetFOMs:
                print expfile
                continue
            fomFuncs = [func for func in self.allFuncs if func.func_name in targetFOMs]
            for funcToRun in fomFuncs:
                fname = funcToRun.func_name
                fdict = self.funcDicts[fname]
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
            self.testWithJSON(expfile)

    def processFuncs(self):
        self.params = {}
        self.funcDicts = {}
        for func in self.allFuncs:
            fname = func.func_name
            funcdict = {'batchvars': [], 'params': []}
            dictargs = func.func_code.co_argcount - len(func.func_defaults)
            funcdict['numdictargs'] = dictargs
            arglist = zip(func.func_code.co_varnames[dictargs:], func.func_defaults)
            for arg, val in arglist:
                if isinstance(val, list):
                    funcdict['batchvars'].append(arg)
                    funcdict['~'+arg] = val
                #elif (val in RAW_DATA) or (val in INTER_DATA):
                # we can't check this ^ if we process function before looking at data
                # so instead just check if it's a string and assume it's data
                #   (new version tester should verify this somehow)
                elif isinstance(val, str):
                    funcdict[arg] = val
                else:
                    self.params[fname+'_'+arg] = val
                    funcdict['params'].append(arg)
                    funcdict['#'+arg] = val
            self.funcDicts[fname] = funcdict

    def requestParams(self):
        for fname in self.funcDicts.keys():
            fdict = self.funcDicts[fname]
            if fdict.get('params'):
                #usedefault = distutils.util.strtobool(raw_input("Use default parameters for "+fname+"? "))
                # uncomment ^ this line to take parameters from user
                usedefault = True #THIS IS FOR TESTING ONLY
                if not usedefault:
                    for param in fdict.get('params'):
                        newval = raw_input(param+": ")
                        self.params[fname+'_'+param] = attemptnumericconversion(newval)
                        fdict['#'+param] = attemptnumericconversion(newval)

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

    def testWithJSON(self, expfilepath):
        expfilename = os.path.split(expfilepath)[1][:-4]
        savepath = jsontranslator.toJSON(expfilename+'v1',
                                         self.FOMs, self.interData, self.params)
        jsontranslator.fromJSON(savepath)

def makeFileRunner(args):
    return FileRunner(*args)

class FileRunner(object):
    def __init__(self, expfile, modname, paramdict, funcdicts):
        self.txtfile = expfile
        self.modname = modname
        self.params = paramdict
        self.fdicts = funcdicts
        self.run()

    def run(self):
        funcMod = __import__(self.modname)
        allFuncs = [f[1] for f in getmembers(funcMod, isfunction)]
        # RUN ON ONE FILE
        # intermediate data and figures of merit are different for every file
        self.interData = {}
        self.FOMs = {}
        rawdatafile = readechemtxt(self.txtfile)
        with open(rawdatafile) as rawdata:
            self.rawData = pickle.load(rawdata)
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
        self.testWithXML(self.txtfile)
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

    def testWithJSON(self, expfilepath):
        expfilename = os.path.split(expfilepath)[1][:-4]
        savepath = jsontranslator.toJSON(expfilename+'v1',
                                         self.FOMs, self.interData, self.params)
        jsontranslator.fromJSON(savepath)

    def testWithXML(self, expfilepath):
        expfilename = os.path.split(expfilepath)[1][:-4]
        savepath = os.path.join('C:\Users\shubauer\Desktop\Working folder\AutoAnalysisXML',
                                expfilename+'v1.xml')
        dataTup = (self.FOMs, self.interData, self.params)
        xmltranslator.toXML(savepath, '1', dataTup)
