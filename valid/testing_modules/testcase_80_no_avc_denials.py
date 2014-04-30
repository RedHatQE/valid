""" This module contains testcase_80_no_avc_denials test """
from valid.valid_testcase import ValidTestcase


class testcase_80_no_avc_denials(ValidTestcase):
    """
    Check for avc denials absence
    """
    tags = ['default']
    stages = ['stage1', 'stage2']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'cat /var/log/messages /var/log/audit/audit.log | grep -v userdata | grep \'avc:[[:space:]]*denied\'', 60, 1)

        return self.log
