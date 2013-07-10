from lxml import etree
import numpy
import ast, distutils.util

numpy.set_printoptions(threshold=numpy.nan)

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
            fignode.text = str(val)
            if isinstance(val, numpy.ndarray):
                fignode.set("type", type(val).__name__+"_"+
                            type(val[0]).__name__)
            else:
                fignode.set("type", type(val).__name__)
    treeToFile = etree.ElementTree(root)
    treeToFile.write(filepath, pretty_print=True)
    return root

# NOTE: There's a loss of precision in converting floats to strings
#   and back to floats.  It might be reasonable to pickle the intermediate
#   data as well.
def getDataFromXML(filepath):
    fomDict = {}
    intermedDict = {}
    paramDict = {}
    dtypes = {"int": int, "int_": int, "float": float, "float_": float,
              "float32": numpy.float32, "float64": numpy.float64,
              "int32": numpy.int32, "int64": numpy.int64}
              #"bool": bool, "bool_": bool}
    with open(filepath, 'rb') as xmlfile:
        docTree = etree.parse(xmlfile)
    version = docTree.getroot().get("version")
    fomTree = docTree.find("figures_of_merit")
    intermedTree = docTree.find("intermediate_values")
    paramTree = docTree.find("function_parameters")
    for node, datadict in zip((fomTree, intermedTree, paramTree),
                              (fomDict, intermedDict, paramDict)):
        for fig in node.iter("figure"):
            figtype = fig.get("type")
            if figtype in dtypes:
                dtypeFunc = dtypes.get(figtype)
                datadict[fig.get("name")] = dtypeFunc(fig.text)
            elif "ndarray" in figtype:
                valtype = figtype.partition('_')[2]
                if valtype in dtypes:
                    datadict[fig.get("name")] = numpy.fromstring(fig.text[1:-1],
                                                                 dtype = dtypes.get(valtype),
                                                                 sep = ' ')
                # since non-empty strings evaluate to true when converted
                #   to boolean, we need to use the special "strtobool"
                #   function to evaluate "False" to False
                elif "bool" in valtype:
                    datadict[fig.get("name")] = numpy.array(map(
                        distutils.util.strtobool, fig.text[1:-1].split()),
                                                            dtype=bool)
                else:
                    print "unrecognized type in array:", valtype
            else:
                print "unrecognized type:", figtype
    return (version, fomDict, intermedDict, paramDict)
