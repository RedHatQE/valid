""" Result parsing functions """
import textwrap

COMMON_COMMAND_KEYS_ORDERED=('command', 'match', 'result', 'value', 'actual', 'expected', 'comment')

def command_repr(command):
    '''repr a single command as list of lines'''
    ret = []
    format_value = lambda key, value: textwrap.wrap(('%s: ' % key) + str(value), initial_indent='  ', subsequent_indent='  ',
                        break_on_hyphens=False,  break_long_words=True, width=70)
    ret.append('-')
    for key in COMMON_COMMAND_KEYS_ORDERED:
        if key not in command:
            continue
        ret.extend(format_value(key, command[key]))
    for key in set(command) - set(COMMON_COMMAND_KEYS_ORDERED):
        ret.extend(format_value(key, command[key]))
    return ret

def get_overall_result(ami, verbose=False):
    """ Get human-readable representation of the result; partitioned by instance """

    arch = ami['arch']
    product = ami['product']
    region = ami['region']
    version = ami['version']
    ami_result = ami['result']
    overall_result = 'succeeded'
    bug_summary = ami['ami'] + ' ' + product + ' ' + version + ' ' + arch + ' ' + region
    bug_description = []

    for itype in ami_result.keys():
        instance_result = 'succeeded'
        itype_description = []
        itype_result = ami_result[itype]
        if type(itype_result) == dict:
            for stage in sorted(itype_result.keys()):
                test_result = itype_result[stage]
                if type(test_result) == list:
                    is_failed = 'succeeded'
                    for command in test_result:
                        if command['result'] in ['fail', 'failed', 'failure']:
                            is_failed = 'failed'
                            if instance_result == 'succeeded':
                                instance_result = 'failure'
                        if command['result'] in ['skip', 'skipped']:
                            is_failed = 'skipped'
                        if command['result'] in ['warn', 'warning']:
                            is_failed = 'warning'
                    itype_description.append('test %s %s' % (stage, is_failed))
                    if is_failed != 'succeeded' or verbose:
                        for command in test_result:
                            if is_failed != 'warning' or command['result'] in ['warn', 'warning'] or verbose:
                                   itype_description.extend(command_repr(command))
                elif test_result == 'skip':
                    itype_description.append('%s: test skipped' % stage)
                else:
                    itype_description.append('%s: test failure' % stage)
                    instance_result = 'failure'
        else:
            itype_description.append('instance testing failed!')
            overall_result = 'failure'
        if overall_result == 'succeeded' and instance_result == 'failure':
            overall_result = 'failure'
        itype_header = '%s -- %s' % (itype, instance_result)
        itype_description.insert(0, '-' * len(itype_header))
        itype_description.insert(0, itype_header)
        bug_description.append('\n'.join(itype_description))
    info = '# Validation %s for %s, %s. Product: %s, %s, %s.' % (overall_result, ami["ami"], region, product, version, arch)
    return (overall_result, bug_summary, info, bug_description)
