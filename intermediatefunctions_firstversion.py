# written by John Gregoire
# modified by Allison Schubauer and Daisy Hernandez
# Created: 6/24/2013
# Last Updated: 7/23/2013
# For JCAP
# first version of helper/intermediate data functions for automated
#   data processing

import numpy

""" Calculates the average time step between data measurements during
    the experiment. """
def calcmeandt(rawd, interd):
    interd['dt']=(rawd['t(s)'][1:]-rawd['t(s)'][:-1]).mean()
    return

""" Based on scipy cookbook. x is 1-d array, window is the number of points used to smooth the data,
    order is the order of the smoothing polynomial, will return the smoothed "deriv"th derivative of x. """
def savgolsmooth(x, nptsoneside=7, order = 4, dx=1.0, deriv=0, binprior=0):
    if nptsoneside<=1:
        return x
    if binprior>1:
        origlen=len(x)
        x=numpy.array([x[i*binprior:(i+1)*binprior].mean() for i in range(origlen//binprior)])
        dx*=binprior
    side=numpy.uint16(max(nptsoneside, numpy.ceil(order/2.)))
    s=numpy.r_[2*x[0]-x[side:0:-1],x,2*x[-1]-x[-2:-1*side-2:-1]]
    # a second order polynomal has 3 coefficients
    b = numpy.mat([[k**i for i in range(order+1)] for k in range(-1*side, side+1)])
    m = numpy.linalg.pinv(b).A[deriv] #this gives the dth ? of the base array (.A) of the pseudoinverse of b

    # precompute the offset values for better performance
    offsets = range(-1*side, side+1)
    offset_data = zip(offsets, m)

    smooth_data=[numpy.array([(weight * s[i + offset]) for offset, weight in offset_data]).sum() for i in xrange(side, len(s) - side)]
    smooth_data=numpy.array(smooth_data)/(dx**deriv)
    
    if binprior>1:    
        ia=numpy.arange(binprior, dtype='float32')/binprior
        xr=numpy.concatenate([ia*(b-a)+a for a, b in zip(smooth_data[:-1], smooth_data[1:])])
        xr=numpy.concatenate([(smooth_data[1]-smooth_data[0])*ia[:binprior//2]+smooth_data[0], xr, (smooth_data[-1]-smooth_data[-2])*ia[:binprior//2]+smooth_data[-1]])
        smooth_data=numpy.concatenate([xr, (smooth_data[-1]-smooth_data[-2])*ia[:origlen-len(xr)]+smooth_data[-1]])

    return smooth_data

""" Produces a list of dictionaries containing information about each
    time segment of the experiment. """
def calcsegind(rawd, interd, SGpts=10):
    if not 'dt' in interd.keys():
        calcmeandt(rawd, interd)
    interd['Ewe(V)_dtSG']=savgolsmooth(rawd['Ewe(V)'], nptsoneside=SGpts, order = 1, dx=interd['dt'], deriv=1, binprior=0)
    rising=interd['Ewe(V)_dtSG']>=0
    interd['segind']=numpy.empty(len(rising), dtype='uint16')
    endptcorr=int(1.5*SGpts)#remove possibilities of segment breaks within 1.5SGpts of the edges
    rising[:endptcorr+1]=rising[endptcorr+2]
    rising[-endptcorr-1:]=rising[-endptcorr-2]
    inds=numpy.where(rising[:-1]!=rising[1:])[0]
    inds=numpy.concatenate([[0], inds, [len(rising)]])
    for count, (i0, i1) in enumerate(zip(inds[:-1], inds[1:])):
        interd['segind'][i0:i1]=count
    interd['segprops_dlist']=[]
    for si, i0 in zip(range(interd['segind'].max()+1), inds[:-1]):
        interd['segprops_dlist']+=[{}]
        interd['segprops_dlist'][-1]['rising']=rising[i0+1]
        inds2=numpy.where(interd['segind']==si)[0]
        interd['segprops_dlist'][-1]['inds']=inds2
        interd['segprops_dlist'][-1]['npts']=len(interd['segprops_dlist'][-1]['inds'])
        interd['segprops_dlist'][-1]['dEdt']=interd['Ewe(V)_dtSG'][inds2][SGpts:-SGpts].mean()

def arrayzeroind1d(arr, postoneg=False, negtopos=True):
    sarr=numpy.sign(arr)
    if postoneg:
        zeroind=numpy.where(sarr[:-1]>sarr[1:])[0]
        if negtopos:
            zeroind=numpy.append(zeroind, numpy.where(sarr[:-1]*sarr[1:]<=0)[0])
    else:#assume that if not postoneg then negtopos
        zeroind=numpy.where(sarr[:-1]*sarr[1:]<=0)[0]
    #returns array of the floating point "index" linear interpolation between 2 indices
    return (1.0*zeroind*arr[(zeroind+1,)]-(zeroind+1)*arr[(zeroind,)])/(arr[(zeroind+1,)]-arr[(zeroind,)])

def calccurvregions(rawd, interd, SGpts=10, critfracposcurve=.95, curvetol=3.e-5):
    interd['I(A)_dtdtSG']=numpy.empty(rawd['I(A)'].shape, dtype='float32')
    interd['I(A)_dtSG']=numpy.empty(rawd['I(A)'].shape, dtype='float32')
    for segd in interd['segprops_dlist']:
        inds=segd['inds']
        interd['I(A)_dtSG'][inds]=numpy.float32(
            savgolsmooth(rawd['I(A)'][inds], nptsoneside=SGpts, order = 2, dx=interd['dt'], deriv=1, binprior=0))
        interd['I(A)_dtdtSG'][inds]=numpy.float32(
            savgolsmooth(interd['I(A)_dtSG'][inds], nptsoneside=SGpts, order = 2, dx=interd['dt'], deriv=1, binprior=0))
        
        startatend=segd['rising']       
        
        if startatend:
            arr=interd['I(A)_dtdtSG'][inds][::-1]
        else:
            arr=interd['I(A)_dtdtSG'][inds]
        arr+=curvetol #curve to line?
        zinds=arrayzeroind1d(arr, postoneg=True, negtopos=False)
        zinds.sort()
        zinds=numpy.array(zinds, dtype='int32')
        posarr=arr>=0
        starti=numpy.where(posarr)[0][0]
        if len(zinds)==0 and numpy.all(posarr):
            cutoffind=len(arr)
        else:
            if len(zinds)==0:
                zinds=numpy.array([len(arr)])
            cutoffinds=[zi for zi in zinds if (posarr[starti:zi].sum(dtype='float32'))/(zi-starti)
                        > critfracposcurve]
            if len(cutoffinds)==0:
                # no suitable positive curvature region found
                cutoffind=starti
            else:
                cutoffind=max(cutoffinds)
        
        if startatend:
            segd['anreginds']=inds[::-1][starti:cutoffind][::-1]
        else:
            segd['anreginds']=inds[starti:cutoffind]
        segd['poscurveinds']=segd['anreginds'][interd['I(A)_dtdtSG'][segd['anreginds']]>0]

def findlinearsegs(y, dydev_frac,  dydev_nout, dn_segstart,  SGnpts=10, dx=1., dydev_abs=0.,
                   maxfracoutliers=.5, critdy_fracmaxdy=None, critdy_abs=None, npts_SGconstdy=2):
    if 2*npts_SGconstdy+dydev_nout>=len(y):
        # array not long enough to find linear segments
        return [], [], [], [], []
    dy=savgolsmooth(y, nptsoneside=SGnpts, order = 2, dx=dx, deriv=1)
    lenconstdy=numpy.array([(dy[i]==0. and (0, ) or \
    (numpy.all(numpy.abs(dy[i:]-dy[i])<max(numpy.abs(dy[i]*dydev_frac), dydev_abs)) and (len(dy)-i, ) or \
    (numpy.where(numpy.logical_not(numpy.abs(dy[i:]-dy[i])<max(numpy.abs(dy[i]*dydev_frac), dydev_abs)))[0][:dydev_nout][-1],)))[0] for i in range(len(dy)-dydev_nout)])
    
    if len(lenconstdy)==0:
        len_segs=[]
        istart_segs=[]
    else:
        lendn=savgolsmooth(numpy.float32(lenconstdy), nptsoneside=npts_SGconstdy, order = 1, dx=1.0, deriv=1, binprior=0)
        istart_segs=numpy.where((lendn[:-1]>0)&(lendn[1:]<0))[0]
        if numpy.any(lenconstdy[:npts_SGconstdy+1]>=lenconstdy[npts_SGconstdy+1]):
            itemp=numpy.argmax(lenconstdy[:npts_SGconstdy])
            if not itemp in istart_segs:
                istart_segs=numpy.append(itemp, istart_segs)
        istart_segs[(istart_segs<npts_SGconstdy*2)]=npts_SGconstdy*2
        istart_segs[(istart_segs>len(y)-1-npts_SGconstdy*2)]=len(y)-1-npts_SGconstdy*2
        istart_segs+=numpy.array([numpy.argmax(lenconstdy[i-npts_SGconstdy*2:i+npts_SGconstdy*2]) for i in istart_segs])-npts_SGconstdy*2
        istart_segs=numpy.array(clustercoordsbymax1d(lenconstdy, istart_segs, dn_segstart))
        istart_segs=istart_segs[lenconstdy[istart_segs]>=dydev_nout/maxfracoutliers]
        len_segs=lenconstdy[istart_segs]

    if not critdy_abs is None:
        critdy_fracmaxdy=critdy_abs/numpy.abs(dy).max()
    if not critdy_fracmaxdy is None:
        istart_constsegs, len_constsegs, garb, garb=findzerosegs(dy, critdy_fracmaxdy,  dydev_nout, dn_segstart,
                                                                 SGnpts=SGnpts, plotbool=plotbool, dx=1., maxfracoutliers=maxfracoutliers)
        temp=[[i, l] for i, l in zip(istart_constsegs, len_constsegs) if numpy.min((istart_segs-i)**2)>dn_segstart**2]
        if len(temp)>0:
            istart_constsegs, len_constsegs=numpy.array(temp).T
            istart_segs=numpy.append(istart_segs, istart_constsegs)
            len_segs=numpy.append(len_segs, len_constsegs)        
    if len(istart_segs)==0:
        return numpy.array([]), numpy.array([]), numpy.array([]), numpy.array([]), dy
    fitdy_segs, fitinterc_segs=numpy.array([numpy.polyfit(dx*(i+numpy.arange(l)), y[i:i+l], 1) for i, l in zip(istart_segs, len_segs)]).T
    return istart_segs, len_segs, fitdy_segs, fitinterc_segs, dy

def findzerosegs(y, yzero_maxfrac, ydev_nout, dn_segstart, SGnpts=10, dx=1., maxfracoutliers=.5):
    # ydev_nout is number of outliers allowed in segment, dn_segstart is how close to each other
    #   the segments are allowed to start
    if ydev_nout>=len(y):
        # array not long enough to find zero segments
        return [], [], [], []
    y=savgolsmooth(y, nptsoneside=SGnpts, order = 2)
    yzero_maxfrac=numpy.abs(y).max()*yzero_maxfrac
    lenzeroy=numpy.array([\
    (numpy.all(numpy.abs(y[i:])<=yzero_maxfrac) and (len(y)-i, ) or \
    (numpy.where(numpy.abs(y[i:])>yzero_maxfrac)[0][:ydev_nout][-1],))[0] for i in range(len(y)-ydev_nout)])

    nptstemp=2
    lendn=savgolsmooth(numpy.float32(lenzeroy), nptsoneside=nptstemp, order = 1, dx=1.0, deriv=1, binprior=0)
    
    
    istart_segs=numpy.where((lendn[:-1]>0)&(lendn[1:]<0))[0]
    if numpy.any(lenzeroy[:nptstemp+1]>=lenzeroy[nptstemp+1]):
        itemp=numpy.argmax(lenzeroy[:nptstemp])
        if not itemp in istart_segs:
            istart_segs=numpy.append(itemp, istart_segs)
    istart_segs[(istart_segs<nptstemp*2)]=nptstemp*2
    istart_segs[(istart_segs>len(y)-1-nptstemp*2)]=len(y)-1-nptstemp*2
    istart_segs+=numpy.array([numpy.argmax(lenzeroy[i-nptstemp*2:i+nptstemp*2])
                              for i in istart_segs])-nptstemp*2
    istart_segs=numpy.array(clustercoordsbymax1d(lenzeroy, istart_segs, dn_segstart))
    istart_segs=istart_segs[lenzeroy[istart_segs]>ydev_nout/maxfracoutliers]
    
    if len(istart_segs)==0:
        return numpy.array([]), numpy.array([]), numpy.array([]), numpy.array([])
        
    len_segs=lenzeroy[istart_segs]

    fitdy_segs, fitinterc_segs=numpy.array(
        [numpy.polyfit(dx*(i+numpy.arange(l)), y[i:i+l], 1)
         for i, l in zip(istart_segs, len_segs)]).T

    return istart_segs, len_segs, fitdy_segs, fitinterc_segs # fit intercept is wrt the beginning of the array, index=0 not x=0

def SegSG(rawd, interd, SGpts=10, order=1, k='I(A)'):
    kSG=k+'_SG'
    if k in rawd:
        data = rawd[k]
    else:
        data = interd[k]
    interd[kSG]=numpy.zeros(data.shape, dtype='float32')
    for segd in interd['segprops_dlist']:
        inds=interd['inds']
        interd[kSG][inds]=numpy.float32(savgolsmooth(data[inds], nptsoneside=SGpts, order = order, deriv=0, binprior=0))

def SegdtSG(rawd, interd, SGpts=10, order=1, k='I(A)', dxk='dt'):
    kSG=k+'_dtSG'
    if not k in (rawd.keys() + interd.keys()) and dxk in interd.keys():
        return
    if k in rawd:
        data = rawd[k]
    else:
        data = interd[k]
    interd[kSG]=numpy.zeros(data.shape, dtype='float32')
    for segd in interd['segprops_dlist']:
        inds=segd['inds']
        interd[kSG][inds]=numpy.float32(savgolsmooth(
            data[inds], nptsoneside=SGpts, order = order, deriv=1, binprior=0, dx=interd[dxk]))
    return

def calcLinSub(rawd, interd, var='I(A)', dydev_frac=0.02, dydev_nout=10, dydev_abs=0.5e-5,
               Vsegrange=0.1, minslope=-1e-6):
    dn_segstart=3*dydev_nout
    dx = interd['dt']
    if var in rawd:
        data = rawd[var]
    else:
        data = interd[var]
    interd[var+'_LinSub']=numpy.zeros(data.shape, dtype='float32')
    for segd in interd['segprops_dlist']:
        try:
            y=data[segd['inds']]
            istart_segs, len_segs, fitdy_segs, fitinterc_segs, dy = findlinearsegs(
                y, dydev_frac,  dydev_nout, dn_segstart, dydev_abs=dydev_abs, dx=dx, critdy_fracmaxdy=None)

            if len(istart_segs)==0:
                # no linear segments within this segment
                continue
            v0v1=numpy.array([rawd['Ewe(V)'][segd['inds']][i0:i0+l][[0, -1]] for i0, l in zip(istart_segs, len_segs)])
            dE_segs=v0v1[:, 1]-v0v1[:, 0]
            segi=numpy.where(((dE_segs)>Vsegrange)&(fitdy_segs>minslope))[0]
            if len(segi)>0:
                seli=segi[numpy.argmin(fitdy_segs[segi])]
            else:
                segi=numpy.where(fitdy_segs>minslope)[0]
                seli=segi[numpy.argmin(fitdy_segs[segi])]
            dysel=fitdy_segs[seli]
            intsel=fitinterc_segs[seli]
            ylin=intsel+dysel*numpy.arange(len(y))*dx
            interd['SegIndStart_LinSub']=istart_segs[seli]
            interd['LinLen_LinSub']=len_segs[seli]
            interd['Intercept_LinSub']=intsel
            interd['dIdt_LinSub']=dysel
            interd[var+'_LinSub'][segd['inds']]=numpy.float32(y-ylin)
            return 1
        except:
            return 0

    dIdEcrit=.0005
    SegdtSG(dlist, SGpts=10, order=1, k='I(A)_LinSub', dxk='dE')
    if not 'I(A)_LinSub_dtSG' in interd.keys():
        return
    for segd in d['segprops_dlist'][:1]: #only 0 and 1 again?
        y=interd['I(A)_LinSub_dtSG'][segd['inds']]
        x=interd['Ewe(V)_SG'][segd['inds']]
        starti=numpy.where(y<dIdEcrit)[0][-1]+1
        if starti<len(y):
            interd['dIdE_aveabovecrit']=y[starti:].mean()
            interd['E_dIdEcrit']=x[starti]
        else:
            interd['dIdE_aveabovecrit']=float('nan')
            interd['E_dIdEcrit']=float('nan')

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
        # no light cycles
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
        try:
            interd[k+'_ill']=getillvals(rawd[k])
            interd[k+'_dark']=getdarkvals(rawd[k])
        except KeyError:
            interd[k+'_ill']=getillvals(interd[k])
            interd[k+'_dark']=getdarkvals(interd[k])
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
        # no light cycles
        return 1
    riseinds=riseinds[riseinds<fallinds[-1]]#only consider illum if there is a dark before and after
    fallinds=fallinds[fallinds>riseinds[0]]
    if len(fallinds)<2 or len(riseinds)==0:
        # no light cycles
        return 1
    ill_istart, ill_len=istart_len_calc(riseinds, fallinds, illfracrange)
    darkstart, darkend=numpy.where(numpy.logical_not(illum))[0][[0, -1]]
    dark_istart, dark_len=istart_len_calc(numpy.concatenate([[darkstart], fallinds]), numpy.concatenate([riseinds, [darkend]]), darkfracrange)

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
        try:
            interd[k+'_ill']=getillvals(rawd[k])
            interd[k+'_dark']=getdarkvals(rawd[k])
        except KeyError:
            interd[k+'_ill']=getillvals(interd[k])
            interd[k+'_dark']=getdarkvals(interd[k])
    for k in ykeys:
        interd[k+'_illdiff']=d[k+'_ill']-0.5*(interd[k+'_dark'][:-1]+interd[k+'_dark'][1:])
        interd[k+'_illdiffmean']=numpy.mean(interd[k+'_illdiff'])
        interd[k+'_illdiffstd']=numpy.std(interd[k+'_illdiff'])
    return 0
