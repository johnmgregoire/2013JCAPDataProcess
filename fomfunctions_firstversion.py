# John Gregoire
# Modified: Allison Schubauer and Daisy Hernandez
# Created: 6/25/2013
# Last Updated: 6/26/2013
# For JCAP

""" Calculate the steadystate mean. This is done by breaking the x into
    pieces each of the size of TestPts. We try to add more and more test
    points to the range that will produce our steadystate mean. This is done
    without adding more noise by checking the value of the standard deviation
    of that range weighted accordingly. The value of WeightExp is in order to
    weight the importance of std and the number of points. """
def CalcArrSS(x, WeightExp=1., TestPts=10):
    p=WeightExp
    i=TestPts
    s0=x[:i].std()/i**p+1
    while x[:i].std()/i**p<s0 and i<len(x):
        s0=x[:i].std()/i**p
        i+=TestPts
    return x[:i].mean()

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

""" gives you the average of the steadystate region """
def CalcAvg(x, t, interval, numStdDevs, numPts, startAtEnd=0):
    # if we wish to start the end, reverse the lists
    if startAtEnd:
        x = x[::-1]
        t = t[::-1]
    # restricts x to requested t-interval    
    x = x[numpy.abs(t-t[0])<interval]
    # removes outliers using mean and std
    x=removeoutliers_meanstd(x, numPts//2, numStdDevs) # // = integer division
    # the mean of the data now that outliers have been removed
    return x.mean()

""" Calculates the first E value at which I crosses the threshold. """
def CalcE_IThresh(i, v, iThresh, numConsecPts,noThresh,setAbove=1):
    if not setAbove: # 0 for below, 1 for above
        i *= -1
        iThresh *= -1
    # returns and array of same size with each index having a 0 or 1
    # if at that index i >= iThresh, than there is a 1 else a 0
    keyPts = numpy.int16(i >= iThresh)
    # Checks each index that can create a range of numConsecPts
    # consecutive points. Range is then checked to see if everything
    # in there is a 1. Only points that can create this range are in
    # keyPtsConsec. 
    keyPtsConsec = [keyPts[x:x+numConsecPts].prod()
               for x in range(len(keyPts)-numConsecPts)]
    # see if there is any range in there than is a 1
    if True in keyPtsConsec:
        # since there is, get the index
        ival = keyPtsConsec.index(True)
        # get this first range and return the mean
        return v[ival:ival+numConsecPts].mean()
    else:
        # no range was found given the parameters, return noThresh
        return noThresh

