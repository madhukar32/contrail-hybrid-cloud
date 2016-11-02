import logging
import os

class hybridLogger(object):

    DEBUG = logging.debug
    INFO  = logging.info
    WARN  = logging.warning
    ERROR = logging.error
    CRITICAL = logging.critical

    @staticmethod
    def log(level='INFO', defaultPath='hybrid.log', envKey='LOG_FILE', name=__name__):

        path = defaultPath
        value = os.getenv(envKey, None)
        filePath = ""

        if value:
            filePath = value.rpartition('/')[0]
            path = value
        
        if os.path.exists(filePath):
            pass
        else:
            print "path given in LOG_FILE environment varibale doesnt exist, changed to default path"
            path = defaultPath

        if level == 'INFO':
            level == hybridLogger.INFO
        elif level == 'DEBUG':
            level == hybridLogger.DEBUG
        elif level == 'WARN':
            level == hybridLogger.WARN
        elif level == 'ERROR':
            level == hybridLogger.ERROR
        elif level == 'CRITICAL':
            level == hybridLogger.CRITICAL
        else:
            print 'Improper logging level, please check your input'
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # create a file fileHandler
        fileHandler = logging.FileHandler(path)
        fileHandler.setLevel(level)

        # create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(formatter)

        # add the fileHandlers to the logger
        logger.addHandler(fileHandler)

        #create a stream handler for console
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(level)
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)
        return logger

