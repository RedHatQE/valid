""" This module contains testcase_39_root_is_locked test """
from valid.valid_testcase import ValidTestcase


class testcase_39_root_is_locked(ValidTestcase):
    """
    Root account should be locked
    """
    tags = ['default']
    stages = ['stage1']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, r'egrep "^root:(\!\!|\*|x|locked):" /etc/shadow')
        return self.log
