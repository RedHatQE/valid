""" This module contains testcase_15_rhel_version test """
from valid.valid_testcase import ValidTestcase
import re


class testcase_15_rhel_version(ValidTestcase):
    """
    Check redhat-release version
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        if prod in ['RHEL', 'BETA'] and params['version'].startswith('7.'):
            rhelv = self.match(connection, 'rpm -q --qf \'%{VERSION}\n\' --whatprovides redhat-release',
                               re.compile(r'.*\r\n([0-9]\.[0-9]+)\r\n.*', re.DOTALL))
        else:
            rhelv = self.match(connection, 'rpm -q --qf \'%{RELEASE}\n\' --whatprovides redhat-release',
                               re.compile(r'.*\r\n([0-9]\.[0-9]+\..*)\r\n.*', re.DOTALL))
        if rhelv:
            self.get_return_value(connection, '[ \'%s\' = \'%s\' ]' % (params['version'], rhelv[0][:len(params['version'])]))
        return self.log
