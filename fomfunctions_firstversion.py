# written by John Gregoire
# edited by Allison Schubauer and Daisy Hernandez
# 6/26/2013
# first version of figure of merit functions for automated
#   data processing

from intermediatefunctions_firstversion import numpy
import intermediatefunctions_firstversion as inter

# this dictionary is required to know which figures of merit should
#   be calculated for each type of experiment
# TO DO: come up with a better naming convention for this dictionary
validFuncs = {'CV': {'Max': [['I(A)']], 'Min': [['I(A)']], 'E_IThresh': [],
                     'IllDiff': [['I(A)', 'max'], ['I(A)', 'min']]},
              'OCV': {'Final': [['Ewe(V)']], 'Avg': [['Ewe(V)']],
                      'ArrSS': [['Ewe(V)']], 'IllDiff': [['Ewe(V)', 'avg']]},
              'CP': {'Final': [['Ewe(V)']], 'Avg': [['Ewe(V)']],
                     'ArrSS': [['Ewe(V)']], 'IllDiff': [['Ewe(V)', 'avg']]},
              'CA': {'Final': [['I(A)']], 'Avg': [['I(A)']],
                     'ArrSS': [['I(A)']], 'IllDiff': [['I(A)', 'avg']]}}

def ArrSS(rawd, x=['Ewe(V)', 'I(A)'], weightExp=1., numTestPts=10):
    x = rawd[x]
    i=numTestPts
    s0=x[:i].std()/i**weightExp+1
    while x[:i].std()/i**weightExp<s0 and i<len(x):
        s0=x[:i].std()/i**weightExp
        i+=numTestPts
    return x[:i].mean()

def E_IThresh(rawd, i='I(A)', v='Ewe(V)', iThresh=1e-5, numConsecPts=20,
                  setAbove=1, noThresh=1.):
    i = rawd[i]
    v = rawd[v]
    if not setAbove: # 0 for below, 1 for above
        i *= -1
        iThresh *= -1
    keyPts = numpy.int16(i >= iThresh)
    keyPtsConsec = [keyPts[x:x+numConsecPts].prod()
                    for x in range(len(keyPts)-numConsecPts)]
    if True in keyPtsConsec:
        ival = keyPtsConsec.index(True)
        return v[ival:ival+numConsecPts].mean()
    else:
        # return value indicating threshold not reached
        return noThresh

def Avg(rawd, x=['Ewe(V)', 'I(A)'], t='t(s)', interval=1000, numStdDevs=2.,
            numPts=1000, startAtEnd=0):
    x = rawd[x]
    t = rawd[t]
    # if we wish to start at the end, reverse the lists
    if startAtEnd:
        x = x[::-1]
        t = t[::-1]
    # restricts x to requested t-interval    
    x = x[numpy.abs(t-t[0])<interval]
    # removes outliers using mean and std
    x=inter.removeoutliers_meanstd(x, numPts//2, numStdDevs) # // = integer division
    # the mean of the data now that outliers have been removed
    return x.mean()

def Final(rawd, x=['Ewe(V)', 'I(A)']):
    return rawd[x][-1]
    
def Max(rawd, x=['Ewe(V)', 'I(A)']):
    return numpy.max(rawd[x])

def Min(rawd, x=['Ewe(V)', 'I(A)']):
    return numpy.min(rawd[x])

def IllDiff(rawd, interd, illum='Illum', thisvar=['Ewe(V)', 'I(A)'],
                othervar='I(A)', t='t(s)', fomName=['min', 'max', 'avg'],
                lightStart=0.4, lightEnd=0.95, darkStart =0.4, darkEnd=0.95,
                illSigKey='Ach(V)', sigTimeShift=0., illThresh=0.8,
                illInvert=1):
    if thisvar == 'I(A)':
        othervar = 'Ewe(V)'
    if sigTimeShift:
        # add intermediate value 'IllumMod'
        interd['IllumMod']=inter.illumtimeshift(rawd, illSigKey, t, sigTimeShift)
        illSigKey = 'IllumMod'
        if illInvert: # logical invert
            # multiply illumination signal by -1
            interd['IllumMod'] *= -1
    elif illInvert: # logical invert
        # add intermediate value 'IllumMod'
        # multiply illumination signal by -1
        interd['IllumMod'] = -1*rawd[illSigKey]
        illSigKey = 'IllumMod'
    err = inter.calcdiff_ill_caller(rawd, interd, ikey = illSigKey,
                                           thresh = illThresh, ykeys = [thisvar],
                                           xkeys = [othervar, t],
                                           illfracrange = (lightStart, lightEnd),
                                           darkfracrange = (darkStart, darkEnd))
    if err:
        # if this is not an illumination experiment, intermediate
        #   illumination values aren't necessary (ASK JOHN)
        """for illIntermed in filter(lambda intermed: 'ill' in intermed.lower(),
                                  interd.keys()):
            del(interd[illIntermed])"""
        return 0.
    if fomName == 'min':
        return min(interd[thisvar+'_illdiff'])
    if fomName == 'max':
        return max(interd[thisvar+'_illdiff'])
    else:
        return interd[thisvar+'_illdiffmean']
