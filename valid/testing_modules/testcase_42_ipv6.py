from valid.valid_testcase import *


class testcase_42_ipv6(ValidTestcase):
    """
    Check that ipv6 networking is disabled
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        self.get_return_value(connection, 'grep NETWORKING_IPV6=no /etc/sysconfig/network')
        return self.log
