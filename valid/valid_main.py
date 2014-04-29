import logging
import multiprocessing
import os
import sys
import re
import yaml
import urllib2
import getpass
import subprocess
import traceback
import string
import random

from valid import valid_worker, valid_watchman, valid_server
from valid.testing_modules import *
from valid import cloud

def strzero(value, maxvalue):
    """
    Generate string from number with leading zeros to save lexicographical order

    @param value: value to represent as string
    @type value: int

    @param maxvalue: maximum allowed value
    @type maxvalue: int

    @return: string with leading zeros
    @rtype: str
    """
    result = str(value)
    while len(result) < len(str(maxvalue)):
        result = '0' + result
    return result


class ValidMain(object):
    def __init__(self):
        self.logger = logging.getLogger('valid.runner')

        self.debug = False
        self.config = '/etc/validation.yaml'
        self.cloud_access = None
        self.https = None
        self.global_setup_script = None
        self.resultdic = None
        self.resultdic_yaml = None
        self.mailfrom = None
        self.minprocesses = 8
        self.maxprocesses = 32
        self.settlewait = 30
        self.maxtries = 30
        self.maxwait = 90
        self.resdir = '/var/lib/valid'
        self.disable_stages = set()
        self.enable_stages = None
        self.disable_tags = set()
        self.enable_tags = set('default')
        self.disable_tests = set()
        self.enable_tests = None
        self.repeat = 1
        self.hname = '0.0.0.0'
        self.port = 8080
        self.hwp_filter = '.*'
        self.emails = None
        self.subject = None
        self.mailfrom = 'root@localhost'
        
        # Manager
        self.manager = multiprocessing.Manager()

        # number of running processes
        self.numprocesses = self.manager.Value('i', 0)

        # exit
        self.time2die = self.manager.Value('b', False)

        # last testing result
        self.last_testing_exitstatus = self.manager.Value('i', 0)

        # main queue for worker processes
        self.mainq = self.manager.Queue()

        # resulting dictionary
        self.resultdic = self.manager.dict()

        # resulting dictionary YAML
        self.resultdic_yaml = self.manager.dict()

    def start(self):
        """ Do sanity checks and start required processes """

        if self.debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        logging.getLogger('valid.runner').setLevel(loglevel)
        logging.getLogger('valid.testcase').setLevel(loglevel)

        with open(self.config, 'r') as confd:
            yamlconfig = yaml.load(confd)
            if 'cloud_access' in yamlconfig:
                # new-style config
                self.cloud_access = yamlconfig.get('cloud_access', {})
                self.https = yamlconfig.get('https', None)
                self.global_setup_script = yamlconfig.get('global_setup_script', None)
            else:
                # old-style config
                self.logger.warn("Your %s config format is obsolete, it won't be supported forever. Consider switching to new-style config.", self.config)
                self.cloud_access = {'ec2': {'ec2_access_key': yamlconfig['ec2']['ec2-key'],
                                             'ec2_secret_key': yamlconfig['ec2']['ec2-secret-key'],
                                             'ssh': yamlconfig['ssh']}}
                self.https = {'server_ssl_ca': yamlconfig['server_ssl_ca'],
                              'server_ssl_cert': yamlconfig['server_ssl_cert'],
                              'server_ssl_key': yamlconfig['server_ssl_key']}
                self.global_setup_script = yamlconfig.get('setup', None)

        # Check if result directory is writable
        try:
            with open(self.resdir + '/.valid.tmp', 'w') as fdtest:
                fdtest.write('temp')
            os.unlink(self.resdir + '/.valid.tmp')
        except IOError, err:
            self.logger.error('Failed to create file in %s: %s ', self.resdir, err)
            sys.exit(1)

        # hwp filter sanity check
        try:
            re.compile(self.hwp_filter)
        except re.error as err:
            self.logger.error('Error compiling hwp-filter: %s: %s', self.hwp_filter, err)
            sys.exit(1)

        for _ in range(self.minprocesses):
            # Creating minimum amount of worker processes
            wprocess = valid_worker.WorkerProcess(self)
            with self.manager.Lock():
                self.numprocesses.value += 1
            wprocess.start()

        watchprocess = valid_watchman.WatchmanProcess(self)
        watchprocess.start()

    def start_https_server(self):
        """ Start https server """

        self.time2die.set(False)
        # check keys
        if self.https is None:
            self.logger.error('No \'https\' section in config file')
            sys.exit(1)

        for keyfile in self.https['server_ssl_ca'], self.https['server_ssl_cert'], self.https['server_ssl_key']:
            if not os.path.exists(keyfile):
                self.logger.error('File %s does not exist but required for server mode. Use valid_cert_creator.py to create it.', keyfile)
                sys.exit(1)
        hostname = ''
        try:
            self.logger.debug('Trying to fetch real hostname from EC2')
            response = urllib2.urlopen('http://169.254.169.254/latest/meta-data/public-hostname', timeout=5)
            hostname = response.read()
            self.logger.debug('Fetched %s as real hostname')
        except:
            # looks like we're not in EC2 environment
            pass
        if not hostname or hostname == '':
            hostname = subprocess.check_output(['hostname', '-f'])[:-1]
        self.mailfrom = getpass.getuser() + '@' + hostname
        self.logger.debug('Will send resulting emails from ' + self.mailfrom)

        # Starting ServerProcess
        sprocess = valid_server.ServerProcess(self)
        sprocess.start()

    def add_data_file(self, datafile):
        """ Add testing data file """
        result = None
        try:
            with open(datafile, 'r') as datafd:
                data2add = yaml.load(datafd)
                result = self.add_data(data2add)
        except Exception, err:
            self.logger.error('Failed to read data file %s with error %s', datafile, err)
            sys.exit(1)
        return result

    def add_data(self, data, emails=None, subject=None):
        """
        Add testing data
        @param data: list of data fields
        @type params: list

        @param emails: comma-separated list of emails interested in result
        @type emails: str

        @param subject: email subject
        @type subject: str

        @return: transaction id or None
        @rtype: str or None
        """
        transaction_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
        self.logger.info('Adding validation transaction ' + transaction_id)
        transaction_dict = {}
        count = 0
        for params in data:
            cloud_name = params.get('cloud', 'ec2')
            params['cloud'] = cloud_name

            driver = cloud.get_driver(cloud_name, self.logger, self.maxwait)

            if not cloud_name in self.cloud_access:
                self.logger.error('No cloud access data for %s in config', cloud_name)
                continue
            mandatory_fields = ['product', 'arch', 'version', 'ami'] + driver.mandatory_fields
            data_is_valid = True
            for field in mandatory_fields:
                if not field in params:
                    self.logger.error('Missing %s in params', field)
                    data_is_valid = False
            if not data_is_valid:
                continue

            if not 'region' in params:
                params['region'] = 'default'

            if params['ami'] in transaction_dict.keys():
                self.logger.error('Ami %s was already added for transaction %s!', params['ami'], transaction_id)
                continue
            self.logger.debug('Got valid data line ' + str(params))
            hwp_found = False
            for hwpdir in ['hwp', '/usr/share/valid/hwp']:
                try:
                    hwpfd = open(hwpdir + '/' + params['arch'] + '.yaml', 'r')
                    hwp = yaml.load(hwpfd)
                    hwpfd.close()
                    # filter hwps based on args
                    hwp = [x for x in hwp if re.match(self.hwp_filter, x['cloudhwname']) is not None]
                    if not len(hwp):
                        # precautions
                        self.logger.info('no hwp match for %s; nothing to do', self.hwp_filter)
                        continue

                    self.logger.info('using hwps: %s', reduce(lambda x, y: x + ', %s' % str(y['cloudhwname']), hwp[1:], str(hwp[0]['cloudhwname'])))
                    ninstances = 0
                    for hwp_item in hwp:
                        params_copy = {par: str(params[par]) for par in params}
                        params_copy.update(hwp_item)

                        if not 'enable_stages' in params_copy:
                            params_copy['enable_stages'] = self.enable_stages
                        if not 'disable_stages' in params_copy:
                            params_copy['disable_stages'] = self.disable_stages
                        if not 'enable_tags' in params_copy:
                            params_copy['enable_tags'] = self.enable_tags
                        if not 'disable_tags' in params_copy:
                            params_copy['disable_tags'] = self.disable_tags
                        if not 'enable_tests' in params_copy:
                            params_copy['enable_tests'] = self.enable_tests
                        if not 'disable_tests' in params_copy:
                            params_copy['disable_tests'] = self.disable_tests

                        if not 'repeat' in params_copy:
                            params_copy['repeat'] = self.repeat

                        if not 'name' in params_copy:
                            params_copy['name'] = params_copy['ami'] + ' validation'

                        driver.set_default_params(params_copy, self.cloud_access)

                        params_copy['transaction_id'] = transaction_id
                        params_copy['iname'] = 'Instance' + str(count) + '_' + transaction_id
                        params_copy['stages'] = self.get_test_stages(params_copy)
                        ninstances += len(params_copy['stages'])
                        if params_copy['stages'] != []:
                            self.logger.info('Adding ' + params_copy['iname'] + ': ' + hwp_item['cloudhwname'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                            self.mainq.put((0, 'create', params_copy))
                            count += 1
                        else:
                            self.logger.info('No tests for ' + params_copy['iname'] + ': ' + hwp_item['cloudhwname'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                    if ninstances > 0:
                        transaction_dict[params['ami']] = {'ninstances': ninstances, 'instances': []}
                        if emails:
                            transaction_dict[params['ami']]['emails'] = emails
                            if subject:
                                transaction_dict[params['ami']]['subject'] = subject
                    hwp_found = True
                    break
                except:
                    self.logger.debug(':' + traceback.format_exc())
            if not hwp_found:
                self.logger.error('HWP for ' + params['arch'] + ' is not found, skipping dataline for ' + params['ami'])
        if count > 0:
            self.resultdic[transaction_id] = transaction_dict
            self.logger.info('Validation transaction ' + transaction_id + ' added')
            return transaction_id
        else:
            self.logger.error('No data added')
            return None

    def get_test_stages(self, params):
        """
        Get list of testing stages

        @param params: list of testing parameters
        @type params: list

        @return: list of all testing stages (e.g. [01stage1testcase01_xx_test,
                 01stage1testcase02_xx_test, ...])
        @rtype: list
        """
        self.logger.debug('Getting enabled stages for %s', params['iname'])
        result = []
        for module_name in sys.modules.keys():
            if module_name.startswith('valid.testing_modules.testcase'):
                self.logger.debug('Checking %s module', module_name)
                test_name = module_name.split('.')[2]
                while True:
                    try:
                        testcase = getattr(sys.modules[module_name], test_name)()
                        self.logger.debug('Got %s testcase', testcase)
                        if test_name in params['disable_tests']:
                            # Test is disabled, skipping
                            self.logger.debug('Test %s is disabled, skipping', test_name)
                            break
                        if params['enable_tests'] and not test_name in params['enable_tests']:
                            # Test is not enabled, skipping
                            self.logger.debug('Test %s is not enabled, skipping', test_name)
                            break
                        if not params['enable_tests']:
                            tags = set(testcase.tags)
                            self.logger.debug('Test %s has following tags: %s', test_name, tags)
                            if len(tags.intersection(params['disable_tags'])) != 0:
                                # Test disabled as it contains disabled tags
                                self.logger.debug('Test %s is disabled by disable_tags (%s), skipping', test_name, params['disable_tags'])
                                break
                            if params['enable_tags'] and len(tags.intersection(params['enable_tags'])) == 0:
                                # Test disabled as it doesn't contain enabled tags
                                self.logger.debug('Test %s is not enabled by enable_tags (%s), skipping', test_name, params['enable_tags'])
                                break
                        applicable_flag = True
                        if hasattr(testcase, 'not_applicable'):
                            self.logger.debug('Checking not_applicable list for ' + test_name)
                            not_applicable = testcase.not_applicable
                            applicable_flag = False
                            for nakey in not_applicable.keys():
                                self.logger.debug('not_applicable key %s %s ... ', nakey, not_applicable[nakey])
                                rexp = re.compile(not_applicable[nakey])
                                if rexp.match(params[nakey]) is None:
                                    applicable_flag = True
                                    self.logger.debug('not_applicable check failed for ' + test_name + ' %s = %s', nakey, params[nakey])
                                else:
                                    self.logger.debug('got not_applicable for ' + test_name + ' %s = %s' % (nakey, params[nakey]))
                        if hasattr(testcase, 'applicable'):
                            self.logger.debug('Checking applicable list for ' + test_name)
                            applicable = testcase.applicable
                            for akey in applicable.keys():
                                self.logger.debug('applicable key %s %s ... ', akey, applicable[akey])
                                rexp = re.compile(applicable[akey])
                                if akey not in params:
                                    self.logger.debug('No %s key for %s', test_name, akey)
                                    applicable_flag = False
                                    break
                                if not rexp.match(params[akey]):
                                    self.logger.debug('Got \'not applicable\' for %s (%s = %s)', test_name, akey, params[akey])
                                    applicable_flag = False
                                    break
                        if not applicable_flag:
                            break
                        for stage in testcase.stages:
                            if stage in params['disable_stages']:
                                # Stage is disabled
                                continue
                            if params['enable_stages'] and not stage in params['enable_stages']:
                                # Stage is not enabled
                                continue
                            # Everything is fine, appending stage to the result
                            result.append(stage + ':' + test_name)
                    except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), err:
                        self.logger.error('bad test, %s %s', module_name, err)
                        self.logger.debug(traceback.format_exc())
                        sys.exit(1)
                    break
        result.sort()
        if params['repeat'] > 1:
            # need to repeat whole test procedure N times
            result_repeat = []
            for cnt in range(1, params['repeat'] + 1):
                for stage in result:
                    result_repeat.append(strzero(cnt, params['repeat']) + stage)
            result = result_repeat
        self.logger.debug('Testing stages %s discovered for %s', result, params['iname'])
        return result

__all__ = ['ValidMain']
