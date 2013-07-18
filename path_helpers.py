# Allison Schubauer and Daisy Hernandez
# Created: 7/12/2013
# Last Updated: 7/15/2013
# For JCAP

import os

""" gets  all the files in the directory that have the given extension """
def getFolderFiles(directory, ext):
    try:
        files = map(lambda p: os.path.normpath(os.path.join(directory, p)),
                                   filter(lambda f: f.endswith(ext), os.listdir(directory)))
        return files
    except:
        raise

""" gets a recent folder based on the assumption that that it is
    named so that it is the the last in alphabetical order
    0 is most recent"""
def getARecentFolder(directory,num):
    sortedDirectories = sorted(os.listdir(directory),reverse=True)
    if num < len(sortedDirectories):
        return os.path.normpath(os.path.join(directory,sortedDirectories[num]))
    else:
        return None

""" gives a path to given directory and with the given extension but has
    the same naming scheme as the given file """
def giveAltPathAndExt(directory,currentpath,extension):
     return os.path.join(directory,os.path.splitext(os.path.basename(currentpath))[0]+ extension)

""" returns the version number from a path to a file of the format
    rawdatafilename_version """
def getVersionFromPath(path):
    return os.path.splitext(os.path.basename)[0].split('_')[1]
