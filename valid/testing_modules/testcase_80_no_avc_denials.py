import paramiko
from valid.valid_testcase import *


class testcase_80_no_avc_denials(ValidTestcase):
    """
    Check for avc denials absence
    """
    tags = ['default']
    stages = ['stage1', 'stage2']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']

        self.get_return_value(connection, 'grep \'avc:[[:space:]]*denied\' /var/log/messages /var/log/audit/audit.log', expected_status=1)

        return self.log
