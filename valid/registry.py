'''Global valid test case registry module'''
import pkg_resources

_CLASS_NAME_BLACKLIST = ('ValidTestcase',)
TEST_CLASSES = {}

class ValidTestcaseMetaClass(type):
    '''Meta class to register a class instances as a valid test class'''
    def __new__(mcs, name, bases, class_dict):
        '''register a mcs at the test_classes list'''
        class_instance = type.__new__(mcs, name, bases, class_dict)
        if name not in _CLASS_NAME_BLACKLIST:
            TEST_CLASSES[name] = (class_instance)
        return class_instance

# load valid test cases
from valid.testing_modules import *

# 3rd-party test classes registry look-up:
for entry_point in pkg_resources.iter_entry_points(group='valid.testing_modules'):
    entry_point.load()
