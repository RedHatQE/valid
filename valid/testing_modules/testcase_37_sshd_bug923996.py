""" This module contains testcase_37_sshd_bug923996 test """
from valid.valid_testcase import ValidTestcase


class testcase_37_sshd_bug923996(ValidTestcase):
    """
    Perform test against bug #923996: multiple PermitRootLogin=... in /etc/ssh/sshd_config
    """
    stages = ['stage2']
    tags = ['default']
    not_applicable = {'product': '(?i)RHEL|BETA', 'version': r'^5\.[123456789]$|^6\.[01234]$'}

    def test(self, connection, params):
        """ Perform test """

        if params['version'].startswith('5.'):
            self.get_return_value(connection, '[ `grep ^PermitRootLogin /etc/ssh/sshd_config | wc -l` -lt 2 ]')
        if params['version'].startswith('6.'):
            self.get_return_value(connection, '[ `grep ^PermitRootLogin /etc/ssh/sshd_config | wc -l` -eq 0 ]')
        return self.log
