from lxml import etree
import numpy
import ctypes, struct, base64
import os.path, ast, distutils.util

numpy.set_printoptions(threshold=numpy.nan)

DTD_DIR = os.path.normpath(os.path.expanduser("~/Documents/GitHub/JCAPDataProcess"))

def toXML(filepath, verNum, dictTup):
    root = etree.Element("data", version=verNum)
    foms = etree.SubElement(root, "figures_of_merit")
    intermeds = etree.SubElement(root, "intermediate_values")
    params = etree.SubElement(root, "function_parameters")
    for datadict, node in zip(dictTup,
                              (foms, intermeds, params)):
        for figname in datadict.keys():
            fignode = etree.SubElement(node, "figure", name=figname)
            val = datadict[figname]
            valtype, encoding, size = getPrimitiveType(val)
            if isinstance(val, numpy.ndarray):
                #hexstr = ''
                #for item in val:
                #    hexstr += struct.pack(encoding, numpy.asscalar(item))
                arrencode = encoding[0]+str(len(val))+encoding[1:]
                hexstr = struct.pack(arrencode, *val.tolist())
                fignode.set("array_length", str(len(val)))
            elif isinstance(val, list):
                arrencode = encoding[0]+str(len(val))+encoding[1:]
                hexstr = struct.pack(arrencode, *val)
                fignode.set("array_length", str(len(val)))
            elif isinstance(val, numpy.generic):
                hexstr = struct.pack(encoding, numpy.asscalar(val))
            else:
                hexstr = struct.pack(encoding, val)
            fignode.text = base64.b64encode(hexstr)
            fignode.set("type", valtype)
            fignode.set("bits", size)
    xmlHeader = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE data SYSTEM "fomdata.dtd">
"""
    with open(filepath, 'w') as xmlfile:
        xmlfile.write(xmlHeader)
        treeToFile = etree.ElementTree(root)
        treeToFile.write(xmlfile, pretty_print=True)
    return root

def getPrimitiveType(obj):
    if isinstance(obj, numpy.ndarray) or isinstance(obj, list):
        return getPrimitiveType(obj[0])
    elif isinstance(obj, numpy.generic):
        if "float" in type(obj).__name__:
            return ("float", "<f", "32")
        elif "int" in type(obj).__name__:
            return ("int", "<i", "32")
        elif "bool" in type(obj).__name__:
            return ("bool", "<?", "8")
        else:
            raise TypeError("Complex numbers are not supported in XML encoded files.")
    elif isinstance(obj, float):
        return ("float", "<f", "32")
    elif isinstance(obj, int):
        return ("int", "<i", "32")
    elif isinstance(obj, bool):
        return ("bool", "<?", "8")
    else:
        raise TypeError("Type %s is not supported in XML encoded files." %type(obj).__name__)

def getDataFromXML(filepath):
    dtypes = {"float": (float, '<f'), "int": (int, '<i'),
              "bool": (bool, '<?')}
    fomDict = {}
    intermedDict = {}
    paramDict = {}
    with open(filepath, 'rb') as xmlfile:
        docTree = etree.parse(xmlfile)
        # get the name of the external DTD
    dtdName = docTree.docinfo.system_url
    dtdPath = os.path.join(DTD_DIR, dtdName)
    dtd = etree.DTD(dtdPath)
    if not dtd.validate(docTree):
        raise SyntaxError("%s is not a valid XML data file."
                          %os.path.basename(filepath))
    version = docTree.getroot().get("version")
    fomTree = docTree.find("figures_of_merit")
    intermedTree = docTree.find("intermediate_values")
    paramTree = docTree.find("function_parameters")
    for node, datadict in zip((fomTree, intermedTree, paramTree),
                              (fomDict, intermedDict, paramDict)):
        for fig in node.iter("figure"):
            figtype = fig.get("type")
            dtypeFunc, encoding = dtypes.get(figtype)
            figlen = fig.get("array_length")
            if figlen:
                encoding = encoding[0]+figlen+encoding[1:]
            figtup = struct.unpack(encoding, base64.b64decode(fig.text))
            if len(figtup) > 1:
                figval = map(dtypeFunc, list(figtup))
            else:
                figval = dtypeFunc(figtup[0])
            datadict[fig.get("name")] = figval
    return (version, fomDict, intermedDict, paramDict)

### NOTE: There's a loss of precision in converting floats to strings
###   and back to floats.  It might be reasonable to pickle the intermediate
###   data as well.
##def getDataFromXML(filepath):
##    fomDict = {}
##    intermedDict = {}
##    paramDict = {}
##    dtypes = {"int": int, "int_": int, "float": float, "float_": float,
##              "float32": numpy.float32, "float64": numpy.float64,
##              "int32": numpy.int32, "int64": numpy.int64}
##              #"bool": bool, "bool_": bool}
##    parser = etree.XMLParser(dtd_validation=True)
##    with open(filepath, 'rb') as xmlfile:
##        try:
##            docTree = etree.parse(xmlfile, parser)
##        except: #XMLSyntaxError
##            # raise error/write to error log
##            return
##    version = docTree.getroot().get("version")
##    fomTree = docTree.find("figures_of_merit")
##    intermedTree = docTree.find("intermediate_values")
##    paramTree = docTree.find("function_parameters")
##    for node, datadict in zip((fomTree, intermedTree, paramTree),
##                              (fomDict, intermedDict, paramDict)):
##        for fig in node.iter("figure"):
##            figtype = fig.get("type")
##            if figtype in dtypes:
##                dtypeFunc = dtypes.get(figtype)
##                datadict[fig.get("name")] = dtypeFunc(fig.text)
##            elif "ndarray" in figtype:
##                valtype = figtype.partition('_')[2]
##                if valtype in dtypes:
##                    datadict[fig.get("name")] = numpy.fromstring(fig.text[1:-1],
##                                                                 dtype = dtypes.get(valtype),
##                                                                 sep = ' ')
##                # since non-empty strings evaluate to true when converted
##                #   to boolean, we need to use the special "strtobool"
##                #   function to evaluate "False" to False
##                elif "bool" in valtype:
##                    datadict[fig.get("name")] = numpy.array(map(
##                        distutils.util.strtobool, fig.text[1:-1].split()),
##                                                            dtype=bool)
##                else:
##                    print "unrecognized type in array:", valtype
##            else:
##                print "unrecognized type:", figtype
##    return (version, fomDict, intermedDict, paramDict)
