""" This module contains testcase_55_yum_group_install test """
from valid.valid_testcase import ValidTestcase


class testcase_55_yum_group_install(ValidTestcase):
    """
    Try to install 'Development tools' group with yum
    """
    stages = ['stage1']
    tags = ['default']
    not_applicable = {"product": "(?i)RHEL|BETA", "version": "6.0"}

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'yum -y groupinstall \'Development tools\'', 900)
        # Checking whether something was installed
        self.get_return_value(connection, 'rpm -q glibc-devel')
        return self.log
