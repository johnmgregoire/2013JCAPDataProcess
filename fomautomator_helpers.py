# Allison Schubauer and Daisy Hernandez
# Created: 7/15/2013
# Last Updated: 7/18/2013
# For JCAP

import path_helpers
import os

""" returns a tuple with the most recent version and previous
    version of the functiions that we use """
def getVersions(directory,fullpath=False):
    currentVersion = path_helpers.getARecentFolder(directory,0) or ''
    previousVersion = path_helpers.getARecentFolder(directory,1) or ''
    if fullpath:
        return currentVersion,previousVersion
    return os.path.basename(currentVersion),os.path.basename(previousVersion)

