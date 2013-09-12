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
EXPERIMENT_FUNCTIONS = {'CV': {'TafelSlopeVPerDec': [], 'TafelEstart': [],
                               'TafelFitVRange': [], 'TafelLogIex': [],
                               'Max': [['I(A)'], ['I(A)_LinSub']], 'Min': [['I(A)'], ['I(A)_LinSub']],
                               'EatIThresh': [['I(A)'], ['I(A)_LinSub']],
                               'IllDiff': [['I(A)', 'max'], ['I(A)', 'min'],
                                 ['I(A)_LinSub', 'max'], ['I(A)_LinSub', 'min']]},
              'OCV': {'Final': [['Ewe(V)']], 'Avg': [['Ewe(V)']],
                      'ArrSS': [['Ewe(V)']], 'IllDiff': [['Ewe(V)', 'avg']]},
              'CP': {'Final': [['Ewe(V)']], 'Avg': [['Ewe(V)']],
                     'ArrSS': [['Ewe(V)']], 'IllDiff': [['Ewe(V)', 'avg']]},
              'CA': {'Final': [['I(A)']], 'Avg': [['I(A)']],
                     'ArrSS': [['I(A)']], 'IllDiff': [['I(A)', 'avg']]}}

zero_thresh = 5.e-8 # threshold below which measured value is equivalent to zero -
                    #   this is a property of the instrument

"""necessary arguments:
    vshift=-(.187-0.045)
    booldev_frac = 0.5
    booldev_nout = 3
    dydev_frac = 0.2
    dydev_nout = 5
    dydev_abs = 0.
    dx = 1.
    maxfracoutliers = 0.5
    critsegVrange = 0.04
    critsegIend = 3.e-5
    critsegVend = 0.36
    SGpts = 10 (nptsoneside for Savitzy-Golay smoothing)
"""
def TafelSlopeVPerDec(rawd, interd, var='I(A)', vshift=-(.187-0.045), boolDevFrac=0.5, boolDevNOut=3,
                      dyDevFrac=0.2, dyDevNOut=5, dyDevAbs = 0.,
                      dx=1., maxFracOutliers=0.5, critSegVRange=0.04, critSegIEnd=3.e-5,
                      critSegVEnd=0.36, SavGolPts=10):
    # initialize the arrays to hold Tafel values (considered both
    #   intermediate data and figures of merit)
    interd['TafelSlope'] = []
    interd['TafelEstart'] = []
    interd['TafelFitErange'] = []
    interd['TafelLogIex'] = []
    booldn_segstart = 3 * boolDevNOut
    dn_segstart = 3 * dyDevNOut
    inter.calcsegind(rawd, interd, SGpts=SavGolPts) # breaks experiment into segments
    inter.calccurvregions(rawd, interd, SGpts=SavGolPts) # runs on all segments
    linsub =  inter.calcLinSub(rawd, interd, var=var) # returns 1 if successful, 0 if not
    if not linsub:
        interd['TafelSlope'] = float('nan')
        interd['TafelEstart'] = float('nan')
        interd['TafelFitErange'] = float('nan')
        interd['TafelLogIex'] = float('nan')
        return float('nan')
    inter.SegSG(rawd, interd, SGpts=SGpts, order=1, k=var+'_LinSub')
    for seg in range(len(interd['segprops_dlist'])):
        inds=interd['segprops_dlist'][seg]['inds']
        i=interd['I(A)_LinSub_SG'][inds]
        v=rawd['Ewe(V)'][inds]+vshift
        posinds=numpy.where(i>zero_thresh)
        invboolarr=numpy.float32(i<=zero_thresh)
        istart_segs, len_segs, fitdy_segs, fitinterc_segs=inter.findzerosegs(
            invboolarr, boolDevFrac,  boolDevNOut, booldn_segstart, SGnpts=SavGolPts,
            dx=dx, maxfracoutliers=maxFracOutliers)
        if len(istart_segs)==0:
            # no Tafel segments
            interd['TafelSlope'].append(float('nan'))
            interd['TafelEstart'].append(float('nan'))
            interd['TafelFitVrange'].append(float('nan'))
            interd['TafelLogIex'].append(float('nan'))
            continue
        ind=numpy.argmax(len_segs)
        i0=istart_segs[ind]
        i1=i0+len_segs[ind]
        taffitinds=numpy.arange(i0, i1)
        interd['segprops_dlist'][seg]['TafelFitInds']=inds[taffitinds]
        i=i[i0:i1]
        i[i<zero_thresh]=zero_thresh #needed due to outliers
        v=v[i0:i1]
        il=numpy.log10(i)
        try:
            istart_segs, len_segs, fitdy_segs, fitinterc_segs, dy=inter.findlinearsegs(
                il, dyDevFrac, dyDevNOut, dn_segstart, dydev_abs=dyDevAbs, dx=dx, critdy_fracmaxdy=None)
        except:
            interd['TafelSlope'].append(float('nan'))
            interd['TafelEstart'].append(float('nan'))
            interd['TafelFitVrange'].append(float('nan'))
            interd['Tafel_logExCurrent'].append(float('nan'))
            continue
        if len(istart_segs)==0:
            # no Tafel segments
            interd['TafelSlope'].append(float('nan'))
            interd['TafelEstart'].append(float('nan'))
            interd['TafelFitVrange'].append(float('nan'))
            interd['TafelLogIex'].append(float('nan'))
            continue
        #only take those segments covering a certain V range and with a min current for the top 10th of the V range
        #   in the segment and positive slope for there on out and then take the steepest one.
        ind=None
        maxdy=0
        npts=critSegVRange/dx
        npts2=max(2, npts//10+1)
        for count2, (it0, slen, dyv) in enumerate(zip(istart_segs, len_segs, fitdy_segs)):
            if slen<npts:
                continue
            it1=it0+slen
            if numpy.mean(i[it1-npts2:it1])<critSegIEnd:
                continue
            if numpy.mean(v[it1-npts2:it1])<critSegVEnd:
                continue
            if numpy.any(dy[it1:]<0.):
                continue
            if dyv>maxdy:
                maxdy=dyv
                ind=count2
        if ind is None:
            # no Tafel segments
            interd['TafelSlope'].append(float('nan'))
            interd['TafelEstart'].append(float('nan'))
            interd['TafelFitVrange'].append(float('nan'))
            interd['TafelLogIex'].append(float('nan'))
            continue
        
        i0=istart_segs[ind]
        i1=i0+len_segs[ind]
        tafinds=numpy.arange(i0, i1)
        it=il[tafinds]
        vt=v[tafinds]
        fitdy, fitint=numpy.polyfit(vt, it, 1)

        interd['TafelSlope'].append(1./fitdy)
        interd['TafelEstart'].append(v[0])
        interd['TafelFitVrange'].append(vt.max()-vt.min())
        interd['TafelLogIex'].append(fitint)

        interd['segprops_dlist'][seg]['TafelInds']=inds[taffitinds][tafinds]
        
    #FOMs (the entire list):
    return interd['TafelSlope']

def TafelEstart(rawd, interd):
    return interd['TafelEstart']

def TafelFitVRange(rawd, interd):
    return interd['TafelFitVrange']

def TafelLogIex(rawd, interd):
    return interd['TafelLogIex']
    

def ArrSS(rawd, interd, x=['Ewe(V)', 'I(A)', 'I(A)_LinSub'],
          weightExp=1., numTestPts=10):
    if x == 'I(A)_LinSub':
        x = interd[x]
    else:
        x = rawd[x]
    i=numTestPts
    s0=x[:i].std()/i**weightExp+1
    while x[:i].std()/i**weightExp<s0 and i<len(x):
        s0=x[:i].std()/i**weightExp
        i+=numTestPts
    return x[:i].mean()

def EatIThresh(rawd, interd, i=['I(A)', 'I(A)_LinSub'], v='Ewe(V)', iThresh=1e-5,
              numConsecPts=20, setAbove=1, noThresh=1.):
    if i == 'I(A)_LinSub':
        i = interd[i]
    else:
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

def Avg(rawd, interd, x=['Ewe(V)', 'I(A)', 'I(A)_LinSub'], t='t(s)', interval=1000,
        numStdDevs=2., numPts=1000, startAtEnd=0):
    if x == 'I(A)_LinSub':
        x = interd[x]
    else:
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

def Final(rawd, interd, x=['Ewe(V)', 'I(A)', 'I(A)_LinSub']):
    if x == 'I(A)_LinSub':
        x = interd[x]
    else:
        x = rawd[x]
    return x[-1]
    
def Max(rawd, interd, x=['Ewe(V)', 'I(A)', 'I(A)_LinSub']):
    if x == 'I(A)_LinSub':
        x = interd[x]
    else:
        x = rawd[x]
    return numpy.max(x)

def Min(rawd, interd, x=['Ewe(V)', 'I(A)', 'I(A)_LinSub']):
    if x == 'I(A)_LinSub':
        x = interd[x]
    else:
        x = rawd[x]
    return numpy.min(x)

def IllDiff(rawd, interd, illum='Illum', thisvar=['Ewe(V)', 'I(A)', 'I(A)_LinSub'],
                othervar='I(A)', t='t(s)', fomName=['min', 'max', 'avg'],
                lightStart=0.4, lightEnd=0.95, darkStart =0.4, darkEnd=0.95,
                illSigKey='Ach(V)', sigTimeShift=0., illThresh=0.8,
                illInvert=1):
    if (thisvar == 'I(A)' or thisvar == 'I(A)_LinSub'):
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
        #   illumination values aren't necessary
        for illIntermed in filter(lambda intermed: 'ill' in intermed.lower(),
                                  interd.keys()):
            del(interd[illIntermed])
        return float('nan')
    if fomName == 'min':
        return min(interd[thisvar+'_illdiff'])
    if fomName == 'max':
        return max(interd[thisvar+'_illdiff'])
    else:
        return interd[thisvar+'_illdiffmean']
