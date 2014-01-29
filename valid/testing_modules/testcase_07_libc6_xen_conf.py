""" This module contains testcase_06_inittab test """

from valid.valid_testcase import ValidTestcase


class testcase_07_libc6_xen_conf(ValidTestcase):
    """
    Check for /etc/ld.so.conf.d/libc6-xen.conf absence on RHEL
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA'}
    tags = ['default']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'test -f /etc/ld.so.conf.d/libc6-xen.conf', expected_status=1)
        return self.log
