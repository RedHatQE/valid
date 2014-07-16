"""
Provides various tags filtering handlers.
Specific tag names (check_keys) can be registered to a specific Factory type.
Allows e.g. ver, vers, version tag keys to be always mapped to VersionCheckFactory.
Fall-back mechanism included: from the most specific type --- version check ---
to the most generic type --- value check/callable.
"""


from distutils.versionpredicate import VersionPredicate
import re
import logging
from collections import defaultdict


LOG = logging.getLogger(__name__)


class FactoryRegistry(type):
    '''maintain a Check type registry in a last-overrides fashion'''
    # use a regexp check unless factory stated here
    _key_check_map = defaultdict(lambda: RegexpCheckFactory)

    def __new__(mcs, name, bases, class_dict):
        '''register at the check factory'''
        class_instance = type.__new__(mcs, name, bases, class_dict)
        for check_key in class_dict.get('check_keys', []):
            LOG.debug('registering ckeck factory pair: %s, %s', check_key, name)
            FactoryRegistry._key_check_map[check_key] = class_instance
        return class_instance

    @classmethod
    def build_check(mcs, applicable=defaultdict(lambda: None), not_applicable=defaultdict(lambda: None)):
        '''
        return a function to check the applicability based on the parameters
        USAGE
            1) create a tag filter check function based on restrictions
            check_function = filter_factory(applicable={'version': 'Whatever (>=1.0, != 42.0)'}, not_applicable={'product': 'AvoidFoo'})
            2) apply the filter to various tags to get a True/False result
            check_function({'version': '1.0', 'product': 'CoolBar'}) == True
            check_function({'version': '42.0', 'product': 'coolBar'}) == False # doesn't match version requirement
            check_function({'version': '1.0', 'product': 'AvoidFoo'}) == False # matches not_applicable product spec
            check_function({'version': '42.0', 'product': 'AvoidFoo'}) == False # doesn't match version requirement and matches not_applicable product spec
        '''
        return lambda check_spec: all([mcs._key_check_map[spec_key](applicable[spec_key])(spec_value) \
                                        for spec_key, spec_value in check_spec.items() if spec_key in applicable]) and \
                                not any([mcs._key_check_map[spec_key](not_applicable[spec_key])(spec_value) \
                                        for spec_key, spec_value in check_spec.items() if spec_key in not_applicable])


class BasicCheckFactory(object):
    '''factory for either custom callable or value check'''

    # Registry call back
    __metaclass__ = FactoryRegistry

    def __init__(self, specification):
        if callable(specification):
            # custom check
            LOG.debug('callable specification')
            self.check = specification
        else:
            LOG.debug('value check')
            self.check = lambda value: value == specification

    def __call__(self, value):
        '''shortcut for self.check(value)'''
        return self.check(value)


class RegexpCheckFactory(BasicCheckFactory):
    '''factory for either regexp or basic check '''
    def __init__(self, specification):
        try:
            pattern = re.compile(specification)
        except (re.error, TypeError) as error:
            LOG.debug('unsuccessfull regexp compilation (%s); trying basic check', error)
            super(RegexpCheckFactory, self).__init__(specification)
        else:
            LOG.debug('using regexp check: re.compile(%s)', specification)
            self.check = pattern.match


class VersionCheckFactory(RegexpCheckFactory):
    '''factory for either version predicate or regexp check'''
    check_keys = ['ver', 'vers', 'version']

    def __init__(self, specification):
        try:
            predicate = VersionPredicate(specification)
        except (ValueError, AttributeError) as error:
            LOG.debug('unsuccessfull predicate compilation (%s); trying regexp check', error)
            super(VersionCheckFactory, self).__init__(specification)
        else:
            LOG.debug('using predicate: %s', predicate)
            self.check = predicate.satisfied_by


def factory(applicable=defaultdict(lambda: None), not_applicable=defaultdict(lambda: None)):
    '''shortcut for FactoryRegistry'''
    return FactoryRegistry.build_check(applicable, not_applicable)
