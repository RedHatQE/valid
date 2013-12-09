from valid.valid_testcase import *


class testcase_42_ipv6(ValidTestcase):
    """
    Check that ipv6 networking is disabled
    """
    stages = ['stage1']
    tags = ['default']
    applicable = {'product': '(?i)RHEL|BETA', "version": "5\..*|6\..*"}

    def test(self, connection, params):
	prod = params['product'].upper()
        if prod in ['RHEL', 'BETA']:
            self.get_return_value(connection, 'grep NETWORKING_IPV6=no /etc/sysconfig/network')
        else:
            self.get_return_value(connection, 'grep NETWORKING_IPV6=yes /etc/sysconfig/network')

        return self.log
