'''
Valid logging customizations
Stolen from http://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility
Usage: from logging_customizations import ValidLogger; logging.setLoggerClass(ValidLogger)
'''

import logging
PROGRESS = logging.INFO + 5

# pylint: disable=too-many-public-methods
class ValidLogger(logging.Logger):
    '''custom logger supporting PROGRESS level messages'''
    def __init__(self, name, level=logging.NOTSET):
        super(ValidLogger, self).__init__(name, level)

    # hack-in new level name
    logging.addLevelName(PROGRESS, 'PROGRESS')
    setattr(logging, 'PROGRESS', PROGRESS)

    def progress(self, msg, *args, **kvs):
        '''log with the progress severity'''
        if self.isEnabledFor(PROGRESS):
            self.log(PROGRESS, msg, *args, **kvs)
