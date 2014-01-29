""" This module contains testcase_35_console test """
from valid.valid_testcase import ValidTestcase


class testcase_35_console(ValidTestcase):
    """
    console output shoud be redirected to serial for for hvm instances
    """
    stages = ['stage1']
    applicable = {'virtualization': 'hvm'}
    tags = ['default']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'grep \'console=ttyS0\' /proc/cmdline')
        return self.log
