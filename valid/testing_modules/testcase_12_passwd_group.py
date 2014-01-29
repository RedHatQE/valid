""" This module contains testcase_12_passwd_group test """
from valid.valid_testcase import ValidTestcase


class testcase_12_passwd_group(ValidTestcase):
    """
    Check for root/nobody/sshd users and root/daemon/bin groups
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*|6.*'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        ver = params['version']

        self.get_return_value(connection, 'grep \'^root:x:0:0:root:/root:/bin/bash\' /etc/passwd')
        self.get_return_value(connection, 'grep \'^nobody:x:99:99:Nobody:/:/sbin/nologin\' /etc/passwd')
        self.get_return_value(connection, 'grep \'^sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin\' /etc/passwd')
        if ver.startswith('5.') or ver[:3] in ['6.0', '6.1', '6.2']:
            self.get_return_value(connection, 'grep \'^root:x:0:root\' /etc/group')
            self.get_return_value(connection, 'grep \'^daemon:x:2:root,bin,daemon\' /etc/group')
            self.get_return_value(connection, 'grep \'^bin:x:1:root,bin,daemon\' /etc/group')
        elif ver.startswith('6.'):
            self.get_return_value(connection, 'grep \'^root:x:0:\' /etc/group')
            self.get_return_value(connection, 'grep \'^daemon:x:2:bin,daemon\' /etc/group')
            self.get_return_value(connection, 'grep \'^bin:x:1:bin,daemon\' /etc/group')
        return self.log
