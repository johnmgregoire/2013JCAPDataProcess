# Allison Schubauer and Daisy Hernandez
# Created: 7/12/2013
# Last Updated: 7/12/2013
# For JCAP

import os

def getFolderFiles(folder, ext):
    fns=os.listdir(folder)
    pathstoread_temp=[os.path.join(folder, fn) for fn in fns if fn.endswith(ext)]
    pathstoread = [os.path.normpath(path) for path in pathstoread_temp]
    return pathstoread
