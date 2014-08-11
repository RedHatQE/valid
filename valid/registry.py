from collections import defaultdict
import logging
logger = logging.getLogger(__name__)

BLACKLIST_CLASS_NAMES = ['ValidTestcase']

TEST_CLASSES = {}
TEST_STAGES = defaultdict(lambda: [])



class TestRegistry(type):
    def __new__(mcs, name, bases, class_dict):
        class_instance = type.__new__(mcs, name, bases, class_dict)
        if name in BLACKLIST_CLASS_NAMES:
            logger.debug('skip %s', name)
            return class_instance
        # register in class-dict
        TEST_CLASSES[name] = class_instance
        # register in stage-dict
        for stage in getattr(class_instance, 'stage', ['default']):
            TEST_STAGES[stage].append(name)
        logger.debug('registered: %s', name)
        return class_instance

__all__ = ['TestRegistry', 'TEST_CLASSES', 'TEST_STAGES', 'BLACKLIST_CLASS_NAMES']
