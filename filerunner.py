# Allison Schubauer and Daisy Hernandez
# Created: 7/17/2013
# Last Updated: 7/25/2013
# For JCAP

import os, sys
import xmltranslator
import jsontranslator
import qhtest
import rawdataparser
import cPickle as pickle
import inspect
import itertools

""" The FileRunner class processes a single raw data file.  When the program
    runs in parallel, each process creates a FileRunner every time it finishes
    a job and receives a new job.  When the program runs sequentially, a
    FileRunner is created and discarded for each file in succession.
"""
class FileRunner(object):

    """ if updating, takes in intermediate data from srcDir and saves it
        to dstDir """
    def __init__(self, queue, expfile, version, lastversion, modname,
## ------- VSHIFT ---------------------------------------------------------------
                 updatemod, newparams, funcdicts, srcDir, dstDir, rawDataDir):#, vshift):
## ------------------------------------------------------------------------------        
        self.txtfile = expfile
        # gets the name of the experiment from the file path
        self.exitSuccess = 0
        self.expfilename = os.path.splitext(os.path.split(self.txtfile)[1])[0]
        self.version = version
        self.dstDir = dstDir
        self.rawDataDir = rawDataDir
        self.fdicts = funcdicts
## ------- VSHIFT --------------------------------------------------------       
##        self.vshift = vshift
## -----------------------------------------------------------------------       
        # If the program is updating, intermediate data from the previous
        #   version of the functions will be imported and used to calculate
        #   new figures of merit.
        updating = False
        pckpath = None
        # Try to open the previous version's intermediate .pck file and
        #   import 'fomfunctions_update.'  If neither of these files exist,
        #   the intermediate data will be written from scratch.
        if lastversion:
            try:
                pckpath = os.path.join(srcDir, self.expfilename+'.pck')
                with open(pckpath, 'r') as pckfile:
                    oldversion, self.FOMs, self.interData, self.params = pickle.load(pckfile)
                if oldversion == lastversion:
                    funcMod = __import__(updatemod)
                    updating = True
            except:
               pass
        if not updating:
            self.FOMs, self.interData, self.params = {}, {}, {}
            funcMod = __import__(modname)
        for param in newparams:

            self.params[param] = newparams[param]
        # look for a raw data dictionary before creating one from the text file
        try:
            rawdatafile = os.path.join(self.rawDataDir,
                                       [fname for fname in os.listdir(self.rawDataDir)
                                        if self.expfilename in fname and
                                        self.expfilename.endswith(".pck")][0])
        except IndexError:
            rawdatafile = rawdataparser.readechemtxt(self.txtfile)
        with open(rawdatafile) as rawdata:
            self.rawData = pickle.load(rawdata)
        # If the raw data is less than 100 lines long, this file will
        #   be skipped.  The raw data length is also used to exclude
        #   non-scalar intermediate data that is not the same length as
        #   the raw data from intermediate XML and JSON files.
        self.rawDataLength = -1
        for variable, val in self.rawData.iteritems():
            # check for data column
            if isinstance(val, jsontranslator.numpy.ndarray):
                self.rawDataLength = len(val)
                break
        # this will happen if the for loop never finds a data column
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
        try:
            # the functions to run for this experiment are specified by
            #   EXPERIMENT_FUNCTIONS in the functions file
            targetFOMs = funcMod.EXPERIMENT_FUNCTIONS[expType]
        except KeyError:
            raise KeyError("Unrecognized experiment type: %s." %expType)
        if not targetFOMs:
            # nothing else to do for this file
            self.exitSuccess = 1
            return
        # a list of function objects
        fomFuncs = [func for func in allFuncs if func.func_name in targetFOMs]
        for funcToRun in fomFuncs:
            fname = funcToRun.func_name
            fdict = self.fdicts[fname]
            # the dictionary positional arguments (rawd and interd)
            fdictargs = validDictArgs[:fdict['numdictargs']]
            # the list of batch variables to be run
            varsetList = targetFOMs[fname]
            # makes sure that fomfunction is run once if there are
            #   no batch variables
            if not varsetList:
                varsetList = [[]]
            for varset in varsetList:
                # run function with correct dictionary positional
                #   arguments and correct values for keyword arguments
                #   (accessDict is called on keyword arguments)
                fom = funcToRun(**dict(zip(funcToRun.func_code.co_varnames[:funcToRun.func_code.co_argcount],
                                            fdictargs+[self.accessDict(fname, varset, argname) for argname
                                            in funcToRun.func_code.co_varnames[fdict['numdictargs']:funcToRun.func_code.co_argcount]])))
                # since figures of merit must be scalar, save lists of
                #   segmented figures of merit separately
                if isinstance(fom, list):
                    for seg, val in enumerate(fom):
                        self.FOMs[('_').join(map(str, varset)
                                             +[fname, str(seg)])] = val
                # label figure of merit with batch variables and function name
                else:
                    self.FOMs[('_').join(map(str, varset)+[fname])] = fom
        # save all dictionaries in pickle file, then remove certain
        #   intermediates, then save JSON and XML files
        self.savePck()
        # remove intermediates that aren't same length as raw data
        self.stripData()
        self.saveJSON()
        self.saveXML()
        self.exitSuccess = 1

    """ returns the correct value for each keyword argument in the
        fom function definition """
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
## ------- VSHIFT --------------------------------------------------------        
##            elif argname == 'vshift':
##                # vshift is an input to the FileRunner 
##                return self.vshift
## -----------------------------------------------------------------------        
            elif (fdict[argname] in self.rawData) or (fdict[argname] in self.interData):
                # raw/intermediate data value
                return fdict[argname]
            else:
                raise ValueError("%s is not a valid function argument." %argname)

    """ removes any non-scalar from the intermediate data dictionary
        that is not an array of the same length as the raw data """
    def stripData(self):
        for ikey, ival in self.interData.items():
            if (isinstance(ival, jsontranslator.numpy.ndarray) or
                isinstance(ival, list)):
                if len(ival) != self.rawDataLength:
                    self.interData.pop(ikey, None)
            if (isinstance(ival, dict)):
                self.interData.pop(ikey, None)

    """ save tuple of self.FOMs, self.interData (complete), and self.params
        in a pickle file of the name expfilename_version.pck """
    def savePck(self):
        savepath = os.path.join(self.dstDir, self.expfilename+'.pck')
        with open(savepath, 'w') as pckfile:
            pickle.dump((self.version, self.FOMs, self.interData,
                         self.params), pckfile)

    """ save tuple of version name, self.FOMs, self.interData (stripped),
        and self.params in a plain-text JSON file (tuple will be turned
        into JSON array and dicts will be turned into JSON objects)
    """
    def saveJSON(self):
        savepath = os.path.join(self.dstDir, self.expfilename+'.json')
        dataTup = (self.FOMs, self.interData, self.params)
        jsontranslator.toJSON(savepath, self.version, dataTup)

    """ Save tuple of self.FOMs, self.interData (stripped), and self.params
        in a base-64 binary-encoded XML file.  The C type and size of the data
        (in bits) is saved with every value.  The version is saved as an
        attribute of the root element.  See fomdata.dtd for the structural
        convention of these XML files. """
    def saveXML(self):
        savepath = os.path.join(self.dstDir, self.expfilename+'.xml')
        dataTup = (self.FOMs, self.interData, self.params)
        xmltranslator.toXML(savepath, self.version, dataTup)
