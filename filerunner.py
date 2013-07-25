# Allison Schubauer and Daisy Hernandez
# Created: 7/17/2013
# Last Updated: 7/17/2013
# For JCAP

import os, sys
import xmltranslator
import jsontranslator
import qhtest
import rawdataparser
import cPickle as pickle
import inspect
import itertools

JSON_PATH = os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisJSON")
INTERMED_PCK_PATH = os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisIntermed")

class FileRunner(object):

    """ initializes a FileRunner which only processes the data of one file"""
    def __init__(self, queue, expfile, xmlpath, version, lastversion, modname,
                 updatemod, newparams, funcdicts, outDir, rawDataDir):
        self.txtfile = expfile
        self.expfilename = os.path.splitext(os.path.split(self.txtfile)[1])[0]
        self.version = version
        self.outDir = outDir
        self.rawDataDir = rawDataDir
        self.fdicts = funcdicts
        # this is probably temporary
        oldversion = None
        self.FOMs, self.interData, self.params = {}, {}, {}
        # if we have a previous version of the module along with a path to the xml file, we check if
        # it is possible to use the update module
        if lastversion and xmlpath:
            oldversion, self.FOMs, self.interData, self.params = xmltranslator.getDataFromXML(xmlpath)
            #oldversion = path_helpers.getVersionFromPath(pckpath)
            #self.FOMs, self.interData, self.params = pickle.load(pckpath)
            if lastversion == oldversion:
                try:
                    funcMod = __import__(updatemod)
                except ImportError:
                    funcMod = __import__(modname)
            else:
                self.FOMs, self.interData, self.params = {}, {}, {}
                funcMod = __import__(modname)
        else:
            funcMod = __import__(modname)
        for param in newparams:
            self.params[param] = newparams[param]
        # look for a raw data dictionary before creating one from the text file
        try:
            rawdatafile = os.path.join(self.rawDataDir,
                                       [fname for fname in os.listdir(self.rawDataDir)
                                        if self.expfilename in fname][0])
        except IndexError:
            rawdatafile = rawdataparser.readechemtxt(self.txtfile)
        with open(rawdatafile) as rawdata:
            self.rawData = pickle.load(rawdata)
        self.rawDataLength = -1
        for variable, val in self.rawData.iteritems():
            if isinstance(val, jsontranslator.numpy.ndarray):
                self.rawDataLength = len(val)
                break
        else:
            raise ValueError("Not a valid raw data file (check .txt or .pck file).")
        # skip this file if it has fewer than 100 lines of data
        if self.rawDataLength < 100:
            return
        # getmembers returns functions in alphabetical order.  We sort these
        #   functions by the line at which they start in the source code so
        #   that they can be run in the correct order.
        allFuncs = [ftup[1] for ftup in sorted(inspect.getmembers(
            funcMod,inspect.isfunction), key=lambda f: inspect.getsourcelines(f[1])[1])]
        validDictArgs = [self.rawData, self.interData]
        expType = self.rawData.get('BLTechniqueName')
        targetFOMs = funcMod.EXPERIMENT_FUNCTIONS.get(expType)
        if not targetFOMs:
            #print self.txtfile
            return
        fomFuncs = [func for func in allFuncs if func.func_name in targetFOMs]
        #print expType,allFuncs
        for funcToRun in fomFuncs:
            fname = funcToRun.func_name
            fdict = self.fdicts[fname]
            fdictargs = validDictArgs[:fdict['numdictargs']]
##            allvarsets = [fdict.get('~'+batch) for batch in fdict.get('batchvars')]
##            commonvars = lambda vartup, varlist: [var for var in varlist if
##                                                  var in vartup]
##            # requires list of lists - I'm not sure if I like this (it's silly for functions
##            #   with one batch variable)
##            for varset in [commonvars(vartup, varlist) for vartup in
##                           itertools.product(*allvarsets) for varlist in
##                           targetFOMs[fname]]:
##                # this is to make up for the fact that commonvars returns empty lists and
##                #   single-argument lists for two or more batch variables
##                if len(varset) == len(fdict.get('batchvars')):
            varsetList = targetFOMs[fname]
            if not varsetList:
                varsetList = [[]]
            for varset in varsetList:
                fom = funcToRun(**dict(zip(funcToRun.func_code.co_varnames[:funcToRun.func_code.co_argcount],
                                            fdictargs+[self.accessDict(fname, varset, argname) for argname
                                            in funcToRun.func_code.co_varnames[fdict['numdictargs']:funcToRun.func_code.co_argcount]])))
                # since figures of merit must be scalar, save lists of
                #   segmented figures of merit separately
                if isinstance(fom, list):
                    for seg, val in enumerate(fom):
                        self.FOMs[('_').join(map(str, varset))
                                  +'_'+fname+'_'+str(seg)] = val
                else:
                    self.FOMs[('_').join(map(str, varset))+'_'+fname] = fom
        # need to save all dictionaries in pickle file, then remove certain
        #   intermediates, then save JSON and XML files
        # TEMPORARY:
        lastDataFile = ''
        if oldversion:
            lastDataFile = os.path.join(INTERMED_PCK_PATH,
                                        self.expfilename+'_'+oldversion+'.pck')
        #self.savePck(INTERMED_PCK_PATH, lastDataFile)
        # remove intermediates that aren't same length as raw data
        self.stripData()
        self.saveJSON(JSON_PATH)
        self.saveXML()
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

    def stripData(self):
        for ikey, ival in self.interData.items():
            if (isinstance(ival, jsontranslator.numpy.ndarray) or
                isinstance(ival, list)):
                if len(ival) != self.rawDataLength:
                    self.interData.pop(ikey, None)

    def savePck(self, directory, oldfilename):
        # remove old version of intermediate data for this file
        if oldfilename:
            os.path.remove(oldfilename)
        savepath = os.path.join(directory, self.expfilename+'_'+self.version+'.pck')
        with open(savepath, 'w') as pckfile:
            pickle.dump((self.FOMs, self.interData, self.params), pckfile)

    def saveJSON(self, directory):
        savepath = os.path.join(directory, self.expfilename+'.json')
        dataTup = (self.FOMs, self.interData, self.params)
        jsontranslator.toJSON(savepath, self.version, dataTup)

    def saveXML(self):
        savepath = os.path.join(self.outDir, self.expfilename+'.xml')
        dataTup = (self.FOMs, self.interData, self.params)
        xmltranslator.toXML(savepath, self.version, dataTup)
