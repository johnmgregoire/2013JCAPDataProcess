# written by John Gregoire
# edited by Allison Schubauer and Daisy Hernandez
# 6/26/2013
# reads raw data from text file and produces a dictionary,
#   which is then saved as a pickle file

import cPickle as pickle
import numpy
import os

if os.path.exists('C://Users//dhernand//Desktop//Working folder//AutoAnalysisFunctions'):
    RAW_DATA_PATH = 'C:\Users\dhernand\Desktop\Working folder\AutoAnalysisPck'
else:
    RAW_DATA_PATH = 'C:\Users\shubauer\Desktop\Working folder\AutoAnalysisPck'

""" read all raw data from file into dictionary """
def readechemtxt(path):
    # TO DO: ask Ed about reliability of database connection
    try:
        datafile = open(path, mode='r')
    except IOError:
        print 'File failed to load. Function will now exit.'
        return
    lines = datafile.readlines()
    datafile.close()
    rawData = {}
    dataCols = []
    for count, line in enumerate(lines):
        # % is line separator for parameter lines
        if line.startswith('%'):
            # x is the separator '='
            key, x, param = line.strip('%').strip().partition('=')
            # strips whitespace
            key = key.strip()
            param = param.strip()
            if key in ('elements', 'column_headings', 'positions'):
                # turns line in file into nicely-formatted list
                val = []
                while len(param) > 0:
                    # b is first value, garb is column separator '\t'
                    #   (garbage ... haha), c is rest of line
                    first, x, param = param.strip().replace('\\t',
                                                           '\t').partition('\t')
                    val.append(first)
                # try to convert strings to float
                if key == 'compositions':
                    val = [attemptnumericconversion(v) for v in val]
                    try:
                        val = numpy.float32(val)
                    except:
                        # want to notify the user if the
                        #   'compositions' field isn't valid -
                        #   this might indicate a bigger problem
                        print 'Not a valid list of compositions'
                        return
            elif key in ('x', 'y'):
                # remove units from x and y values
                val = attemptnumericconversion(param.replace('mm', '').strip())
            elif key == 'Epoch':
                # TO DO: ask John if these need to be named differently
                key = 'mtime'
                val = attemptnumericconversion(param)
            else:
                # convert numerical fields to numbers (ints or floats),
                #   ignore string fields
                val = attemptnumericconversion(param)
            # save all parameters into intermediate dictionary
            #   (should we actually be doing this?)
            rawData[key] = val
        else:
            # stop iterating through lines when you reach data lines
            break
    try:
        # raw data: separate each line by column, convert value to float
        #   as long as line is not empty
        # there might be a better way to do this without the count variable
        # TO DO: figure that ^ out
        dataCols = [map(float, l.strip().replace('\\t', '\t').split('\t'))
                    for l in lines[count:] if len(l.strip()) > 0]
##    except:
##        # not sure if this is a good way to raise an error or not
##        print line
##        print '\t' in line
##        print line.split('\t')
##        print map(float, line.split('\t')) 
##        raise
    # TO DO: figure out if this ^ is necessary
    except:
        pass
    # transpose z so that it's ordered by columns, then associate
    #   columns with their headings in dictionary
    for colName, data in zip(rawData['column_headings'], numpy.float32(dataCols).T):
        rawData[colName] = data
    rawData['path'] = path
    # time to save rawData!
    # get filename from path, remove '.txt' at end
    # TO DO: save this in a specific folder
    filecode = os.path.split(path)[1][:-4]
    savepath = os.path.join(RAW_DATA_PATH, filecode+'.pck')
    with open(savepath, 'wb') as savefile:
        pickle.dump(rawData, savefile)
    return savepath

""" convert a string into an int or float if numeric; otherwise,
    leave string as is """
def attemptnumericconversion(astring):
    try:
        numVal = float(astring)
        if int(numVal) == numVal:
            return int(numVal)
        else:
            return numVal
    except ValueError:
        return astring
