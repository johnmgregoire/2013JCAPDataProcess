# Allison Schubauer and Daisy Hernandez
# Created: 7/17/2013
# Last Updated: 7/17/2013
# For JCAP

import os
import xmltranslator
import qhtest
import rawdataparser
import cPickle as pickle
import inspect
import itertools
import logging

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
            rawdatafile = rawdataparser.readechemtxt(self.txtfile)
        try: 
            with open(rawdatafile) as rawdata:
                self.rawData = pickle.load(rawdata)
        except:
            return

        funcMod = __import__(self.modname)
        allFuncs = [f[1] for f in inspect.getmembers(funcMod, inspect.isfunction)]
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
        processHandler = qhtest.QueueHandler(queue)  
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
