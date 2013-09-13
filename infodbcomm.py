# John Gregoire
# Created: 9/12/2013
# Last Updated: 79/12/2013
# For JCAP

"""
    uses data file names to get experiment ID and query database
    for relevant info to be returned as infoDict.
    Requires Python mysql routines from GitHub JCAPPyDBComm
"""

import sys, os, re


# append the DBComm library to the program's list of libraries to check
#   for modules to import (needed for mysql_dbcommlib)
PyCodePath=os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
sys.path.append(os.path.join(PyCodePath, 'JCAPPyDBComm'))

from mysql_dbcommlib import *

sys.path.append(os.path.join(PyCodePath, 'PythonCodeSecureFiles'))
from paths import *
from echelogin import *



dfltdict=dict([('reference_Eo', 0.), ('technique_name', '')])
def infoDictfromDB(filenames):
    
    recordids=[]
    for fn in filenames:
        dashposns=[i.start() for i in re.finditer('-',fn)]
        if len(dashposns)<4:
            print 'Error: filename has unexpected format so using default reference_Eo and technique_name on ', fn
            dataids+=[-1]
            continue
        recordids+=[fn[dashposns[2]+1:dashposns[3]]]
    
    if max(recordids)<0:
        return [dfltdict]*len(filenames)

    fields=['plate_id', 'sample_no','created_at', 'reference_Eo', 'technique_name']
    dbc=dbcomm(user=user, password=password, db=db)
    infodicts=[]
    for recid, fn in zip(recordids, filenames):
        if recid<0:
            infodicts+=[dfltdict]
            continue
        d=dbc.getrowdict_fields('id', recid, fields, valcvtcstr=None)
        if d['reference_Eo'] is None:
            print 'reference_Eo not defined so using 0 for ', fn
            d['reference_Eo']=0.
        infodicts+=[d]
        
    dbc.db.close()
    return infodicts

    
# plateid, sampleid, epxerimenttime, composition, reference_Eo, technique_name=technique_name
# required to have keys 'reference_Eo' and 'technique_name'
