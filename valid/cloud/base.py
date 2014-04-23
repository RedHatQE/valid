"""
Basic abstract cloud class and exceptions
"""


class TemporaryCloudException(Exception):
    """
    Temporary exception, 'try again'
    """
    pass


class PermanentCloudException(Exception):
    """
    Permanent exception, no need to try any more
    """
    pass


class SkipCloudException(Exception):
    """
    'Skip' exception - missing hardware in the region,...
    """
    pass


class UnknownCloudException(Exception):
    """
    Unknown exception, 'try again' but increase ntry
    """
    pass


class AbstractCloud(object):
    """
    Abstract cloud class
    """
    def __init__(self, logger, maxwait):
        self.logger = logger
        self.maxwait = maxwait

    def create(self, params):
        raise PermanentCloudException("Not implemented")

    def terminate(self, params):
        raise PermanentCloudException("Not implemented")

    def get_console_output(self, params):
        raise PermanentCloudException("Not implemented")
