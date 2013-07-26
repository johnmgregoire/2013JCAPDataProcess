# Allison Schubauer and Daisy Hernandez
# Created: 7/15/2013
# Last Updated: 7/26/2013
# For JCAP

import path_helpers
import os

""" returns a tuple with the most recent version and previous
    version of the functiions that we use """
def getRVersions(directory,fullpath=False):
    currentVersion = path_helpers.getARecentFolder(directory,0) or ''
    previousVersion = path_helpers.getARecentFolder(directory,1) or ''
    if fullpath:
        return currentVersion,previousVersion
    return os.path.basename(currentVersion),os.path.basename(previousVersion)



""" returns a tuple with the desired version and the previous version
    based on the name of the version"""
def getVersionsByName(vpath,fullpath=False):
    currentVersion = vpath or ''
    funcDir = os.listdir(os.path.dirname(vpath))
    funcDir.sort()
    verIndex = funcDir.index(os.path.basename(vpath))
    if verIndex > 0:
        previousVersion = os.path.join(os.path.dirname(vpath),funcDir[verIndex-1])
    else:
       previousVersion = ''
    if fullpath:
        return currentVersion, previousVersion
    return os.path.basename(currentVersion),os.path.basename(previousVersion)
