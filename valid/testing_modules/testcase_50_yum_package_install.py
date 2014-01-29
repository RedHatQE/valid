""" This module contains testcase_50_yum_package_install test """
from valid.valid_testcase import ValidTestcase


class testcase_50_yum_package_install(ValidTestcase):
    """
    Try to install package with yum
    """
    stages = ['stage1']
    tags = ['default']
    not_applicable = {"product": "(?i)RHEL|BETA", "version": "6.0"}

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'yum clean all', 30)
        self.get_return_value(connection, 'yum repolist', 120)
        checkupdate = self.get_return_value(connection, 'yum check-update', 120, nolog=True)
        if not checkupdate in [0, 100]:
            # 100 means 'we have an update'
            self.log.append({"result": "failed", "command": "yum check-update", "actual": str(checkupdate)})
        self.get_return_value(connection, 'yum search zsh', 120)
        self.get_return_value(connection, 'yum -y install zsh', 180)
        self.get_return_value(connection, 'rpm -q --queryformat \'%{NAME}\' zsh', 30)
        self.get_return_value(connection, 'rpm -e zsh', 60)
        return self.log
