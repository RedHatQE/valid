""" Result parsing functions """

def get_overall_result(ami):
    """ Get human-readable representation of the result """

    arch = ami['arch']
    product = ami['product']
    region = ami['region']
    version = ami['version']
    ami_result = ami['result']
    overall_result = 'succeeded'
    bug_summary = ami['ami'] + ' ' + product + ' ' + version + ' ' + arch + ' ' + region
    bug_description = ''

    for itype in ami_result.keys():
        bug_description += itype + '\n'
        itype_result = ami_result[itype]
        if type(itype_result) == dict:
            for stage in sorted(itype_result.keys()):
                test_result = itype_result[stage]
                if type(test_result) == list:
                    is_failed = 'succeeded'
                    for command in test_result:
                        if command['result'] in ['fail', 'failed', 'failure']:
                            is_failed = 'failed'
                            if overall_result == 'succeeded':
                                overall_result = 'failed'
                        if command['result'] in ['skip', 'skipped']:
                            is_failed = 'skipped'
                        if command['result'] in ['warn', 'warning']:
                            is_failed = 'warning'
                    bug_description += 'test %s %s\n' % (stage, is_failed)
                    if is_failed != 'succeeded':
                        for command in test_result:
                            if is_failed != 'warning' or command['result'] in ['warn', 'warning']:
                                bug_description += '--->\n'
                                for key in sorted(command.keys()):
                                    bug_description += '\t%s: %s\n' % (key, command[key])
                                bug_description += '<---\n'
                elif test_result == 'skip':
                    bug_description += '%s: test skipped\n' % stage
                else:
                    bug_description += '%s: test failure\n' % stage
                    overall_result = 'failure'
        else:
            bug_description += 'instance testing failed!\n'
            overall_result = 'failure'
    bug_description = 'Validation %s for %s in %s product: %s, version: %s, arch: %s\n\n%s' % (overall_result,
                                                                                               ami["ami"],
                                                                                               region,
                                                                                               product,
                                                                                               version,
                                                                                               arch,
                                                                                               bug_description)
    return (overall_result, bug_summary, bug_description)
