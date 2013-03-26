from valid.valid_testcase import *


class testcase_37_sshd_bug923996(ValidTestcase):
    """
    Perform test against bug #923996: multiple PermitRootLogin=... in /etc/ssh/sshd_config
    """
    stages = ['stage2']
    tags = ['default']

    def test(self, connection, params):
        self.get_return_value(connection, '[ `grep ^PermitRootLogin /etc/ssh/sshd_config | wc -l` -lt 2 ]')
        return self.log
