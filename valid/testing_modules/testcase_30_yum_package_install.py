from valid.valid_testcase import *

class testcase_30_yum_package_install(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "yum repolist && echo SUCCESS", "\r\nSUCCESS\r\n", 120)
        self.ping_pong(connection, "yum search zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 120)
        self.ping_pong(connection, "yum -y install zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 180)
        self.ping_pong(connection, "rpm -q --queryformat '%{NAME}' zsh && echo", "\r\nzsh\r\n", 30)
        self.ping_pong(connection, "rpm -e zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 60)
        return self.log
