# Allison Schubauer and Daisy Hernandez
# Created: 7/12/2013
# Last Updated: 7/12/2013
# For JCAP

import os

def getFolderFiles(directory, ext):
    return map(lambda p: os.path.normpath(os.path.join(directory, p)),
                               filter(lambda f: f.endswith(ext), os.listdir(directory)))
