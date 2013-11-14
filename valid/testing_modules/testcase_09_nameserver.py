from valid.valid_testcase import *


class testcase_09_nameserver(ValidTestcase):
    """
    Check if nameserver is working
    """

    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        if prod == 'FEDORA':
            self.get_return_value(connection, 'ping -c 5 clock.redhat.com', 30)
        else:
            self.get_return_value(connection, 'dig clock.redhat.com | grep 66.187.233.4', 30)
        return self.log
