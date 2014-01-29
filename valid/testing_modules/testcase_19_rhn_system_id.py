""" This module contains testcase_19_rhn_system_id test """
from valid.valid_testcase import ValidTestcase


class testcase_19_rhn_system_id(ValidTestcase):
    """
    System should not be connected to rhn
    """
    stages = ['stage1']
    tags = ['default']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, '[ ! -f /etc/sysconfig/rhn/systemid ]')
        return self.log
