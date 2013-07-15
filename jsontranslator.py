# Allison Schubauer and Daisy Hernandez
# Created: 6/24/2013
# Last Updated: 6/27/2013
# For JCAP
# functions for converting our formatted data dictionaries to
#   and from JSON files

import os
import csv
import json
import numpy

SAVEPATH = os.path.expanduser("~/Desktop/Working Folder/AutoAnalysisJSON")

def toJSON(filename, fomdict, intermeddict, inputdict):
    savepath = os.path.join(SAVEPATH, filename+'.json')
    with open(savepath, 'w') as fileObj:
        dataTup = (fomdict, intermeddict, inputdict)
        listOfObjs = []
        for dataDict in dataTup:
            listOfObjs.append(convertNpTypes(dataDict))
        json.dump(listOfObjs, fileObj)
    return savepath

def fromJSON(filepath):
    with open(filepath, 'r') as fileObj:
        dataTup = json.load(fileObj, object_hook=unicodeToString)
    print dataTup
    return dataTup

def convertNpTypes(container):
    if isinstance(container, dict):
        pydict = {}
        for key, val in container.iteritems():
            if isinstance(val, numpy.generic):
                val = numpy.asscalar(val)
            elif isinstance(val, numpy.ndarray):
                val = convertNpTypes(list(val))
            pydict[key] = val
        return pydict
    elif isinstance(container, list):
        for i, val in enumerate(container):
            if isinstance(val, numpy.generic):
                container[i] = numpy.asscalar(val)
            elif isinstance(val, numpy.ndarray):
                container[i] = convertNpTypes(list(val))
        return container
    elif isinstance(container, numpy.ndarray):
        return convertNpTypes(list(container))

def unicodeToString(container):
    if isinstance(container, dict):
        strdict = {}
        for key, val in container.iteritems():
            if isinstance(key, unicode):
                key = str(key)
            if isinstance(val, unicode):
                val = str(val)
            elif isinstance(val, list):
                val = unicodeToString(val)
            elif isinstance(val, dict):
                val = unicodeToString(val)
            strdict[key] = val
        return strdict
    elif isinstance(container, list):
        for i, val in enumerate(container):
            if isinstance(val, unicode):
                container[i] = str(val)
            elif isinstance(val, list):
                container[i] = unicodeToString(val)
            elif isinstance(val, dict):
                container[i] = unicodeToString(val)
        return container

def getFOMs(filename):
    dataTup = fromJSON(filename)
    fomdict = dataTup[0]
    idval = filename.split('_')[0]
    with open(filename+'.txt', 'wb') as fileToDB:
        fomwriter = csv.writer(fileToDB)
        rowToWrite = [idval]
        for fom in fomdict:
            rowToWrite.append(str(fom)+': '+str(fomdict.get(fom)))
        fomwriter.writerow(rowToWrite)
    print rowToWrite
