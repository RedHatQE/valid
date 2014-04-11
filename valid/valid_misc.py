import logging
import re
import sys
import traceback
import yaml
import random
import string

from valid.testing_modules import *


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


def get_test_stages(params):
    """
    Get list of testing stages

    @param params: list of testing parameters
    @type params: list

    @return: list of all testing stages (e.g. [01stage1testcase01_xx_test,
             01stage1testcase02_xx_test, ...])
    @rtype: list
    """
    logger = logging.getLogger('valid.runner')
    logger.debug('Getting enabled stages for %s', params['iname'])
    result = []
    for module_name in sys.modules.keys():
        if module_name.startswith('valid.testing_modules.testcase'):
            test_name = module_name.split('.')[2]
            while True:
                try:
                    testcase = getattr(sys.modules[module_name], test_name)()
                    if test_name in params['disable_tests']:
                        # Test is disabled, skipping
                        break
                    if params['enable_tests'] and not test_name in params['enable_tests']:
                        # Test is not enabled, skipping
                        break
                    if not params['enable_tests']:
                        tags = set(testcase.tags)
                        if len(tags.intersection(params['disable_tags'])) != 0:
                            # Test disabled as it contains disabled tags
                            break
                        if params['enable_tags'] and len(tags.intersection(params['enable_tags'])) == 0:
                            # Test disabled as it doesn't contain enabled tags
                            break
                    applicable_flag = True
                    if hasattr(testcase, 'not_applicable'):
                        logger.debug('Checking not_applicable list for ' + test_name)
                        not_applicable = testcase.not_applicable
                        applicable_flag = False
                        for nakey in not_applicable.keys():
                            logger.debug('not_applicable key %s %s ... ', nakey, not_applicable[nakey])
                            rexp = re.compile(not_applicable[nakey])
                            if rexp.match(params[nakey]) is None:
                                applicable_flag = True
                                logger.debug('not_applicable check failed for ' + test_name + ' %s = %s', nakey, params[nakey])
                            else:
                                logger.debug('got not_applicable for ' + test_name + ' %s = %s' % (nakey, params[nakey]))
                    if hasattr(testcase, 'applicable'):
                        logger.debug('Checking applicable list for ' + test_name)
                        applicable = testcase.applicable
                        for akey in applicable.keys():
                            logger.debug('applicable key %s %s ... ', akey, applicable[akey])
                            rexp = re.compile(applicable[akey])
                            if not rexp.match(params[akey]):
                                logger.debug('Got \'not applicable\' for ' + test_name + ' %s = %s', akey, params[akey])
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
                    logger.error('bad test, %s %s', module_name, err)
                    logger.debug(traceback.format_exc())
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
    logger.debug('Testing stages %s discovered for %s', result, params['iname'])
    return result


def add_data(shareddata, data, emails=None, subject=None):
    """
    Add testing data
    @param shareddata: SharedData object
    @type params: SharedData

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
    logger = logging.getLogger('valid.runner')
    logger.info('Adding validation transaction ' + transaction_id)
    transaction_dict = {}
    count = 0
    for params in data:
        mandatory_fields = ['product', 'arch', 'region', 'version', 'ami']
        minimal_set = set(mandatory_fields)
        exact_set = set(params.keys())
        if minimal_set.issubset(exact_set):
            # we have all required keys
            for field in mandatory_fields:
                if type(params[field]) != str:
                    params[field] = str(params[field])
            if params['ami'] in transaction_dict.keys():
                logger.error('Ami %s was already added for transaction %s!', params['ami'], transaction_id)
                continue
            logger.debug('Got valid data line ' + str(params))
            hwp_found = False
            for hwpdir in ['hwp', '/usr/share/valid/hwp']:
                try:
                    hwpfd = open(hwpdir + '/' + params['arch'] + '.yaml', 'r')
                    hwp = yaml.load(hwpfd)
                    hwpfd.close()
                    # filter hwps based on args
                    hwp = [x for x in hwp if re.match(shareddata.hwp_filter, x['ec2name']) is not None]
                    if not len(hwp):
                        # precautions
                        logger.info('no hwp match for %s; nothing to do', shareddata.hwp_filter)
                        continue

                    logger.info('using hwps: %s', reduce(lambda x, y: x + ', %s' % str(y['ec2name']), hwp[1:], str(hwp[0]['ec2name'])))
                    ninstances = 0
                    for hwp_item in hwp:
                        params_copy = params.copy()
                        params_copy.update(hwp_item)
                        if not 'bmap' in params_copy.keys():
                            params_copy['bmap'] = [{'name': '/dev/sda1', 'size': '15', 'delete_on_termination': True}]
                        if not 'userdata' in params_copy.keys():
                            params_copy['userdata'] = None
                        if not 'itype' in params_copy.keys():
                            params_copy['itype'] = 'hourly'

                        if not 'enable_stages' in params_copy:
                            params_copy['enable_stages'] = shareddata.enable_stages
                        if not 'disable_stages' in params_copy:
                            params_copy['disable_stages'] = shareddata.disable_stages
                        if not 'enable_tags' in params_copy:
                            params_copy['enable_tags'] = shareddata.enable_tags
                        if not 'disable_tags' in params_copy:
                            params_copy['disable_tags'] = shareddata.disable_tags
                        if not 'enable_tests' in params_copy:
                            params_copy['enable_tests'] = shareddata.enable_tests
                        if not 'disable_tests' in params_copy:
                            params_copy['disable_tests'] = shareddata.disable_tests

                        if not 'repeat' in params_copy:
                            params_copy['repeat'] = shareddata.repeat

                        if not 'name' in params_copy:
                            params_copy['name'] = params_copy['ami'] + ' validation'

                        params_copy['transaction_id'] = transaction_id
                        params_copy['iname'] = 'Instance' + str(count) + '_' + transaction_id
                        params_copy['stages'] = get_test_stages(params_copy)
                        ninstances += len(params_copy['stages'])
                        if params_copy['stages'] != []:
                            logger.info('Adding ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                            shareddata.mainq.put((0, 'create', params_copy))
                            count += 1
                        else:
                            logger.info('No tests for ' + params_copy['iname'] + ': ' + hwp_item['ec2name'] + ' instance for ' + params_copy['ami'] + ' testing in ' + params_copy['region'])
                    if ninstances > 0:
                        transaction_dict[params['ami']] = {'ninstances': ninstances, 'instances': []}
                        if emails:
                            transaction_dict[params['ami']]['emails'] = emails
                            if subject:
                                transaction_dict[params['ami']]['subject'] = subject
                    hwp_found = True
                    break
                except:
                    logger.debug(':' + traceback.format_exc())
            if not hwp_found:
                logger.error('HWP for ' + params['arch'] + ' is not found, skipping dataline for ' + params['ami'])
        else:
            # we something is missing
            logger.error('Got invalid data line: ' + str(params))
    if count > 0:
        shareddata.resultdic[transaction_id] = transaction_dict
        logger.info('Validation transaction ' + transaction_id + ' added')
        return transaction_id
    else:
        logger.error('No data added')
        return None
