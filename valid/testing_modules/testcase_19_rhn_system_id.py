from valid.valid_testcase import *


class testcase_19_rhn_system_id(ValidTestcase):
    """
    System should not be connected to rhn
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        self.get_return_value(connection, '[ ! -f /etc/sysconfig/rhn/systemid ]')
        return self.log
