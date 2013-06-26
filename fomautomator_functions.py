# Allison Schubauer and Daisy Hernandez
# 6/26/2013
# framework to run all functions in fomfunctions file automatically
#   (still very much in progress)

import cPickle as pickle
from inspect import *
from rawdataparser import *
import fomfunctions_firstversion
import jsontranslator
import distutils.util
import itertools

PARAMS = {}
RAW_DATA = {}
INTER_DATA = {}
FOMS = {}

def processFunc(func):
    global PARAMS
    fname = func.func_name
    funcdict = {'fname': fname, 'batchvars': [], 'params': []}
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
    return funcdict

def requestParams(datadict, fdict):
    if fdict.get('params'):
        fname = fdict.get('fname')
        usedefault = distutils.util.strtobool(raw_input("Use default parameters for "+fname+"? "))
        if not usedefault:
            for param in fdict.get('params'):
                newval = raw_input(param+": ")
                datadict[fname+'_'+param] = attemptnumericconversion(newval)
                fdict['#'+param] = attemptnumericconversion(newval)

def accessDict(fdict, varset, argname):
    fname = fdict.get('fname')
    try:
        # parameter
        return PARAMS[fname+'_'+argname]
    except KeyError:
        if argname in fdict['batchvars']:
            datavar = [var for var in varset if var in fdict['~'+argname]][0]
            return datavar
        elif (fdict[argname] in RAW_DATA) or (fdict[argname] in INTER_DATA):
            # raw/intermediate data value
            return fdict[argname]
        else:
            print argname, "is not a valid argument"


"""data processing for multiple files with multiple functions """
def test():
    global PARAMS
    global RAW_DATA
    global INTER_DATA
    global FOMS
    #raw_data_files = ['622-1-322-232109-20130605141515010PDT.pck', '622-1-322-232164-20130605142813719PDT.pck']
    raw_data_files = ['632-1-327-252803-20130610212436139PDT.pck']
    allFuncs = [f[1] for f in getmembers(fomfunctions_firstversion, isfunction)]
    fdicts = []
    # user-input params for each function are the same for all files in this session
    PARAMS = {}
    for fnum, funcToRun in enumerate(allFuncs):
        fdicts.append(processFunc(funcToRun))
        requestParams(PARAMS, fdicts[fnum])
    for expfile in raw_data_files:
        # intermediate data and figures of merit are different for every file
        INTER_DATA = {}
        FOMS = {}
        with open(expfile) as rawdata:
            RAW_DATA = pickle.load(rawdata)
        validDictArgs = [RAW_DATA, INTER_DATA]
        for fnum, funcToRun in enumerate(allFuncs):
            fdict = fdicts[fnum]
            fdictargs = validDictArgs[:fdict['numdictargs']]
            result = []
            allvarsets = [fdict.get('~'+batch) for batch in fdict.get('batchvars')]
            for varset in itertools.product(*allvarsets):
                fom = funcToRun(**dict(zip(funcToRun.func_code.co_varnames[:funcToRun.func_code.co_argcount],
                                            fdictargs+[accessDict(fdict, varset, argname) for argname
                                            in funcToRun.func_code.co_varnames[fdict['numdictargs']:funcToRun.func_code.co_argcount]])))
                FOMS[('_').join(map(str, varset))+'_'+funcToRun.func_name] = fom
                result.append(fom)
            print expfile, funcToRun.func_name, result
        jsontranslator.toJSON(expfile[:-4]+'v1', FOMS, INTER_DATA, PARAMS)
        jsontranslator.fromJSON(expfile[:-4]+'v1')
