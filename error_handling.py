# Allison Schubauer and Daisy Hernandez
# Created: 6/24/2013
# Last Updated: 6/25/2013
# For JCAP

import logging, logging.handlers

class ErrorHandler():
    
    def __init__(self, name, loggingfile, loglevel = logging.DEBUG):
        # setting up the logger and the messages allowed to be logged
        self.logger = logging.getLogger(name)
        self.logger.setLevel(loglevel)
        # assures that the messages from the logger are propogated upward
        self.logger.propagate
        self.loggingfile = loggingfile

    """ Initializes the file handler. If we are using a child logger then
        we don't have to do this. That is, if we will be relying on the root
        logger and it's file handler. """
    def initHandler(self,formatforhandler=None, logginglevel = logging.DEBUG):
        self.errorFileHandler = self.fileHandlerCreator(self.loggingfile,logginglevel)
        self.initFormat(self.errorFileHandler,formatforhandler)
        self.addHandler(self.errorFileHandler)

    """ Creates a fileHandler and sets its level. This does not have to be done
        more than once if one is planning to rely on a root logger. """
    def fileHandlerCreator(self, filename, logginglevel):
        handler = logging.FileHandler(filename)
        handler.setLevel(logginglevel)
        return handler

    """ Sets the format of the handler it is passed."""
    def initFormat(self,hdlr,formattouse ='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
        formatter = logging.Formatter(formattouse)
        hdlr.setFormatter(formatter)

    """ Adds the handler to the logger created. """
    def addHandler(self,hdlr):
        self.logger.addHandler(hdlr)

    """ Logs the message using different levels. It defaults to DEBUG if
        there is no level given or its not one of the other choices. """
    def logMessage(self,message,level=logging.DEBUG,traceback=False):
        if level == "INFO": level = logging.INFO
        elif level == "WARNING": level = logging.WARNING
        elif level == "ERROR": level = logging.ERROR
        elif level == "CRITICAL": level = logging.CRITICAL
        else: level = logging.DEBUG
        self.logger.log(level,message,exc_info=traceback)

    """ Closes the file handler. If there is more handler those need to be
        closed as well. """
    def close(self):
        self.errorFileHandler.close()



# example of a way to use it
def example(path = 'C:\Users\Public\Documents\errors.log'):     
    testingLog = ErrorHandler('TestingLog', path)
    testingLog.initHandler('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    a = [1,2,3,4,5]
    while True:
        try:
            a.pop()
        except:
                testingLog.logMessage("Failed doing a.pop()")
                break
    testingLog.close()

# comment out to see a demstration of the sample
# example()
