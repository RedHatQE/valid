""" This module contains testcase_40_selinux_context test """
from valid.valid_testcase import ValidTestcase


class testcase_40_selinux_context(ValidTestcase):
    """
    Check selinux context for /etc/{passwd,group} files
    """
    tags = ['default']
    stages = ['stage1']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'ls -lZ /etc/passwd | egrep "system_u:object_r:(etc_t|passwd_file_t)"')
        self.get_return_value(connection, 'ls -lZ /etc/group | egrep "system_u:object_r:(etc_t|passwd_file_t)"')
        return self.log
