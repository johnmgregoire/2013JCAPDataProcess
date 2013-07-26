# Allison Schubauer and Daisy Hernandez
# Created: 7/25/2013
# Last Updated: 7/25/2013
# For JCAP

import sys, os, argparse
import fomautomator
import path_helpers
import fomautomator_helpers
import time

""" this file handles all the commandline flags and runs the fomautomator """
def main(argv):
    parser = argparse.ArgumentParser()
    # possible flags
    parser.add_argument('-I','--inputfolder', type=str, help="The input folder.\
                        All the textfiles of this folder will be processed", nargs=1)
    parser.add_argument('-i', '--inputfile',  type=str, help="The input file.\
                        A single file that will be processed.",  nargs=1)
    parser.add_argument('-f', '--fileofinputs', type=str, help="File containing\
                        paths to input files, each in a new line. Every path\
                        (line) will be passed to the automator for processing", nargs=1)
    parser.add_argument('-J','--jobname', type=str, help="The name you want\
                        to give the log file. It will have a .run extention\
                        while processing. This file will change its extension\
                        if to .done or .error. If more errors than the max\
                        number of errors it will be .error, else .done.",nargs=1)
    parser.add_argument('-O', '--outputfolder', type=str, help="The output\
                        folder where all outputs will be saved. raw data pck\
                        files will be saved here unless -R flag used. ", nargs=1, required=True)
    parser.add_argument('-R', '--rawfolder', type=str, help="The folder where\
                        raw data files will be saved unless. If not used, they\
                        will be saved in the directory specified by -O", nargs=1)
    parser.add_argument('-X', '--errornum', type=int, help="The maximum number of errors - zero or larger", nargs=1)
    parser.add_argument('-P', '--parallel', help="A flag to use parellel\
                        processing. Different than sequential in logging and\
                        max error handling, also mainly used by Gui users.",\
                        action='store_true')
    args = parser.parse_args(argv)

    # the name of the program Module and the update Module
    progModule = "fomfunctions"
    updateModule = "fomfunctions_update"
    # default values that get changed by commandline flags
    paths = []
    outputDir = None
    rawDataDir = None
    jobname = ""
    max_errors = 10
    parallel = False
    # this does not get changed by the commandline, it is currently more useful
    # through the GUI when we do the database connection
    exptypes = []

    if not (args.inputfolder or args.inputfile or args.fileofinputs):
        parser.error('Cannot proceed further as no form of input was specified\
                        Plesase use either -I,-i, or -f.')
        
    if args.inputfolder:
        paths += path_helpers.getFolderFiles(args.inputfolder[0], '.txt')

    if args.inputfile:
        paths += args.inputfolder

    if args.fileofinputs:
        try:
            with open(args.fileofinputs[0], 'r') as fileWithInputFiles:
               paths += fileWithInputFiles.read().splitlines()
        except:
            return "Your file containing input paths has failed, please make\
                    sure there is only one file path per line."
    if args.jobname:
        jobname=args.jobname[0]
    else:
        # use a default jobname - remove if unwanted
        jobname = "job" + time.strftime('%Y%m%d%H%M%S',time.gmtime())
        
    if args.errornum:
        max_errors = args.errornum[0]

    # there is no need to do an else because the flag is required    
    if args.outputfolder:
        outputDir = args.outputfolder[0]
        rawDataDir = args.outputfolder[0]

    # reset the rawDataDir since a directory to save raw data files was given
    if args.rawfolder:
        rawDataDir = args.rawfolder[0]

    if args.parallel:
        parallel = args.parallel

    # gets the most recent version folder of the fomfunctions in the FUNC_DIR
    versionName, prevVersion = fomautomator_helpers.getVersions(fomautomator.FUNC_DIR)
    # inserts only most recent version so correct functions are used
    # as the naming of the function file is the same in all versions
    sys.path.insert(1, os.path.join(fomautomator.FUNC_DIR,versionName))

    if paths:
        automator = fomautomator.FOMAutomator(paths, versionName,prevVersion,progModule,updateModule,exptypes,outputDir,outputDir,max_errors,jobname)
        funcNames, paramsList = automator.requestParams(default=True)
        automator.setParams(funcNames, paramsList)

        # run the automator in the method described by the user
        if parallel:
            automator.runParallel()
        else:
            automator.runSequentially()
        

if __name__ == "__main__":
    main(sys.argv[1:])

# an example of calling it with the command line
# python fom_commandline.py -I "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\5 File" -O "C:\Users\dhernand.HTEJCAP\Desktop\Working Folder\AutoAnalysisXML" -J "jobnametest"
