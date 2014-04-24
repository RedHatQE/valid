import inspect
import sys

from valid.cloud import *

def get_driver(cloud_name, logger, maxwait):
    driver_cls = base.AbstractCloud
    for name, cls in inspect.getmembers(sys.modules["valid.cloud"], inspect.isclass):
        try:
            if getattr(cls, 'cloud') == cloud_name:
                driver_cls = cls
        except:
            pass
    driver = driver_cls(logger, maxwait)
    return driver

