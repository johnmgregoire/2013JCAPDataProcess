# written by John Gregoire
# modified by Allison Schubauer and Daisy Hernandez
# Created: 6/24/2013
# Last Updated: 6/26/2013
# For JCAP
# first version of helper/intermediate data functions for automated
#   data processing

import numpy

""" Averages a maximum of 2*nptoneside neighbor points for each datapoint. It
    uses the datapoints distance from the mean of its neighbors of interest
    and compares it to the the value that is within nsig stdivations from its
    neighbors. If its within the range, it leaves the value, else it replaces it
    with its neighbors mean. The gaptsoneside reduces the neighbors range and
    nptsoneside increases it."""
def removeoutliers_meanstd(arr, nptsoneside, nsig, gapptsoneside=0):
    # only going to use the points directly beside to remove outliers
    if nptsoneside==1 and gapptsoneside==0:
        return removesinglepixoutliers(arr, critratiotoneighbors=nsig)
    nsig=max(nsig, 1.)
    nptsoneside=max(nptsoneside, 2.)
    gapptsoneside=min(gapptsoneside, nptsoneside-2.)
    # work up to decreasing the interval for removing outliers
    # first interval could be something like (0,9) next (1,8) and then (2,7)
    for gap in range(int(round(gapptsoneside+1))):
        # create list of starts and finish for each datapoint
        # combined they give a range that includes the neighbors and the datapoint
        starti=numpy.uint32([max(i-(nptsoneside-gap), 0) for i in range(len(arr))])
        stopi=numpy.uint32([min(i+(nptsoneside-gap)+1, len(arr)) for i in range(len(arr))])

        # i is the index of the datapoint we're working on
        # i0 is where the interval for the neighbors starts
        # i1 is where the interval for the neighbors ends - not included
        # numpy.append(arr[i0:i], arr[i+1:i1] is only the neighbors
        arr=numpy.array([(((numpy.append(arr[i0:i], arr[i+1:i1]).mean()-arr[i]))**2\
                          <(numpy.append(arr[i0:i], arr[i+1:i1]).std()*nsig)**2\
                          and (arr[i],) or (numpy.append(arr[i0:i],arr[i+1:i1]).mean(),))[0]\
                         for i, i0, i1 in zip(range(len(arr)), starti, stopi)],\
                        dtype=arr.dtype)
    return arr

""" Function that removes single pixel outliers. It does this by checking each
    datapoint with two neighbors and checking if it is bigger than both of its
    neighbors times critratiotoneighbors. If it is, then it replaces the value
    by averaging the two neighbors."""
def removesinglepixoutliers(arr,critratiotoneighbors=1.5):
    # Only checks the array without the ends because the ends don't have both
    # a datapoint to the left and the right. It compares this to arrays that
    # are offset by 2 at either the end or beginning. This makes sure to compare
    # each datapoint with the datapoint to its right and to its left. 
    c=numpy.where((arr[1:-1]>(critratiotoneighbors*arr[:-2]))*(arr[1:-1]>(critratiotoneighbors*arr[2:])))
    # We get the index of the points that match both of the comparisons above.
    # We add 1 to account for the fact that indexing was off by 1 since we
    # did not account for either end
    c0=c[0]+1
    arr[c0]=(arr[c0-1]+arr[c0+1])/2
    return arr

def illumtimeshift(rawd, ikey, tkey, tshift):
    tmod=rawd[tkey]-tshift
    inds=[numpy.argmin((t-tmod)**2) for t in rawd[tkey]]
    return rawd[ikey][inds]


def calcdiff_ill_caller(rawd, interd, ikey='Illum', thresh=0, **kwargs):
    try:
        illum=rawd[ikey]>thresh
    except KeyError:
        illum=interd[ikey]>thresh
    riseinds=numpy.where(illum[1:]&numpy.logical_not(illum[:-1]))[0]+1
    fallinds=numpy.where(numpy.logical_not(illum[1:])&illum[:-1])[0]+1
    interd['IllumBool']=illum
    if len(riseinds)==0 or len(fallinds)==0 or (len(riseinds)==1 and len(fallinds)==1 and riseinds[0]>fallinds[0]):
        err=calcdiff_stepill(rawd, interd, ikey=ikey, **kwargs)
    else:
        err=calcdiff_choppedill(rawd, interd, ikey='IllumBool', **kwargs) 
    return err

    
def calcdiff_stepill(rawd, interd, ikey='Illum', ykeys=['Ewe(V)'], xkeys=['t(s)', 'I(A)'], illfracrange=(.4, .95), darkfracrange=(.4, .95)):
    try:
        illum=rawd[ikey]!=0
    except KeyError:
        illum=interd[ikey]!=0
    istart_len_calc=lambda startind, endind, fracrange: (startind+numpy.floor(fracrange[0]*(endind-startind)), numpy.ceil((fracrange[1]-fracrange[0])*(endind-startind)))
    riseinds=numpy.where(illum[1:]&numpy.logical_not(illum[:-1]))[0]+1
    fallinds=numpy.where(numpy.logical_not(illum[1:])&illum[:-1])[0]+1
    
    if len(fallinds)==0 and len(riseinds)==0:
        print 'insufficient light cycles'
        return 1
    if illum[0]:
        illstart=0
        illend=fallinds[0]
        darkstart=fallinds[0]
        if len(riseinds)==0:
            darkend=len(illum)
        else:
            darkend=riseinds[0]
    else:
        darkstart=0
        darkend=riseinds[0]
        illstart=riseinds[0]
        if len(fallinds)==0:
            illend=len(illum)
        else:
            illend=fallinds[0]

    ill_istart, ill_len=istart_len_calc(illstart, illend, illfracrange)
    dark_istart, dark_len=istart_len_calc(darkstart, darkend, darkfracrange)

    inds_ill=[range(int(ill_istart), int(ill_istart+ill_len))]
    inds_dark=[range(int(dark_istart), int(dark_istart+dark_len))]


    interd['inds_ill']=inds_ill
    interd['inds_dark']=inds_dark

    getillvals=lambda arr:numpy.array([arr[inds].mean() for inds in inds_ill])
    getdarkvals=lambda arr:numpy.array([arr[inds].mean() for inds in inds_dark])

    for k in xkeys+ykeys:
        interd[k+'_ill']=getillvals(rawd[k])
        interd[k+'_dark']=getdarkvals(rawd[k])
    for k in ykeys:
        interd[k+'_illdiffmean']=interd[k+'_ill'][0]-interd[k+'_dark'][0]
        interd[k+'_illdiff']=numpy.array(interd[k+'_illdiffmean'])
    return 0
        
def calcdiff_choppedill(rawd, interd, ikey='Illum', ykeys=['I(A)'], xkeys=['t(s)', 'Ewe(V)'], illfracrange=(.4, .95), darkfracrange=(.4, .95)):
    try:
        illum=rawd[ikey]!=0
    except KeyError:
        illum=interd[ikey]!=0
    istart_len_calc=lambda startind, endind, fracrange: (startind+numpy.floor(fracrange[0]*(endind-startind)), numpy.ceil((fracrange[1]-fracrange[0])*(endind-startind)))
    riseinds=numpy.where(illum[1:]&numpy.logical_not(illum[:-1]))[0]+1
    fallinds=numpy.where(numpy.logical_not(illum[1:])&illum[:-1])[0]+1
    if len(fallinds)<2 or len(riseinds)==0:
        print 'insufficient light cycles'
        return 1
    riseinds=riseinds[riseinds<fallinds[-1]]#only consider illum if there is a dark before and after
    fallinds=fallinds[fallinds>riseinds[0]]
    if len(fallinds)<2 or len(riseinds)==0:
        print 'insufficient light cycles'
        return 1
    ill_istart, ill_len=istart_len_calc(riseinds, fallinds, illfracrange)
    darkstart, darkend=numpy.where(numpy.logical_not(illum))[0][[0, -1]]
    dark_istart, dark_len=istart_len_calc(numpy.concatenate([[darkstart], fallinds]), numpy.concatenate([riseinds, [darkend]]), darkfracrange)

    #inds_ill=[range(int(i0), int(i0+ilen)) for i0, ilen in zip(ill_istart, ill_len)]
    #inds_dark=[range(int(i0), int(i0+ilen)) for i0, ilen in zip(dark_istart, dark_len)]

    indstemp=[(range(int(i0ill), int(i0ill+ilenill)), range(int(i0dark), int(i0dark+ilendark))) for i0ill, ilenill, i0dark, ilendark in zip(ill_istart, ill_len, dark_istart, dark_len) if ilenill>0 and ilendark>0]
    inds_ill=map(operator.itemgetter(0), indstemp)
    inds_dark=map(operator.itemgetter(1), indstemp)
    if dark_len[-1]>0:
        inds_dark+=[range(int(dark_istart[-1]), int(dark_istart[-1]+dark_len[-1]))]
    else:
        inds_ill=inds_ill[:-1]

    interd['inds_ill']=inds_ill
    interd['inds_dark']=inds_dark

    getillvals=lambda arr:numpy.array([arr[inds].mean() for inds in inds_ill])
    getdarkvals=lambda arr:numpy.array([arr[inds].mean() for inds in inds_dark])

    for k in xkeys+ykeys:
        interd[k+'_ill']=getillvals(rawd[k])
        interd[k+'_dark']=getdarkvals(rawd[k])
    for k in ykeys:
        interd[k+'_illdiff']=d[k+'_ill']-0.5*(interd[k+'_dark'][:-1]+interd[k+'_dark'][1:])
        interd[k+'_illdiffmean']=numpy.mean(interd[k+'_illdiff'])
        interd[k+'_illdiffstd']=numpy.std(interd[k+'_illdiff'])
    return 0
