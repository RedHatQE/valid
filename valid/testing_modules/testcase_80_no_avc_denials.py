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

        self.ping_pong(connection, 'echo START; grep \'avc:[[:space:]]*denied\' /var/log/messages /var/log/audit/audit.log | grep -v userdata; echo END',
                       '\r\nSTART\r\nEND\r\n', 60)

        return self.log
