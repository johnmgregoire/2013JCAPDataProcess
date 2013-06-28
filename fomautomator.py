# Allison Schubauer and Daisy Hernandez
# 6/26/2013
# framework to run all functions in fomfunctions file automatically

import sys
import cPickle as pickle
from inspect import *
from rawdataparser import *
import jsontranslator
import importlib
import distutils.util
import itertools

PARAMS = {}
RAW_DATA = {}
INTER_DATA = {}
FOMS = {}

class FOMAutomator():
    def __init__(self, rawDataFiles, funcModule):
        self.files = rawDataFiles
        importlib.import_module(funcModule)
        self.module = [sys.modules[mod] for mod in sys.modules
                       if mod == funcModule][0]
        self.allFuncs = [f[1] for f in getmembers(self.module, isfunction)]

    def runSequentially(self):
        global PARAMS
        global RAW_DATA
        global INTER_DATA
        global FOMS
        self.fdicts = {}
        # user-input params for each function are the same for all files in this session
        PARAMS = {}
        self.processFuncs()
        self.requestParams(PARAMS)
        # this is the sequential part
        for expfile in self.files:
            # intermediate data and figures of merit are different for every file
            INTER_DATA = {}
            FOMS = {}
            rawdatafile = readechemtxt(expfile)
            with open(rawdatafile) as rawdata:
                RAW_DATA = pickle.load(rawdata)
            validDictArgs = [RAW_DATA, INTER_DATA]
            expType = RAW_DATA.get('BLTechniqueName')
            print 'expType:', expType
            targetFOMs = self.module.validFuncs.get(expType)
            if not targetFOMs:
                print expfile
                continue
            fomFuncs = [func for func in self.allFuncs if func.func_name in targetFOMs]
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
                        FOMS[('_').join(map(str, varset))+'_'+fname] = fom
            # temporary function to monitor program's output
            self.testWithJSON(expfile)

    def processFuncs(self):
        global PARAMS
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
                    PARAMS[fname+'_'+arg] = val
                    funcdict['params'].append(arg)
                    funcdict['#'+arg] = val
            self.fdicts[fname] = funcdict

    def requestParams(self, datadict):
        for fname in self.fdicts.keys():
            fdict = self.fdicts[fname]
            if fdict.get('params'):
                #usedefault = distutils.util.strtobool(raw_input("Use default parameters for "+fname+"? "))
                # uncomment ^ this line to take parameters from user
                usedefault = True #THIS IS FOR TESTING ONLY
                if not usedefault:
                    for param in fdict.get('params'):
                        newval = raw_input(param+": ")
                        datadict[fname+'_'+param] = attemptnumericconversion(newval)
                        fdict['#'+param] = attemptnumericconversion(newval)

    def accessDict(self, fname, varset, argname):
        fdict = self.fdicts.get(fname)
        try:
            # parameter
            return PARAMS[fname+'_'+argname]
        except KeyError:
            if argname in fdict['batchvars']:
                # retrieve current variable in batch
                datavar = [var for var in varset if var in fdict['~'+argname]][0]
                return datavar
            elif (fdict[argname] in RAW_DATA) or (fdict[argname] in INTER_DATA):
                # raw/intermediate data value
                return fdict[argname]
            else:
                # this error will need to be handled somehow, and this
                #   is something that should definitely be tested in
                #   the committer
                print argname, "is not a valid argument"

    def testWithJSON(self, expfilepath):
        expfilename = os.path.split(expfilepath)[1][:-4]
        savepath = jsontranslator.toJSON(expfilename+'v1', FOMS, INTER_DATA, PARAMS)
        jsontranslator.fromJSON(savepath)
