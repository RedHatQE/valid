from valid.valid_testcase import *
import logging


class testcase_50_yum_package_install(ValidTestcase):
    """
    Try to install package with yum
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        self.get_return_value(connection, 'yum repolist', 120)
        self.get_return_value(connection, 'yum search zsh', 120)
        self.get_return_value(connection, 'yum -y install zsh', 180)
        self.get_return_value(connection, 'rpm -q --queryformat \'%{NAME}\' zsh', 30)
        self.get_return_value(connection, 'rpm -e zsh', 60)
        return self.log
