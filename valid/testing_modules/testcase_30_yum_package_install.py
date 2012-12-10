from valid.valid_testcase import *

class testcase_30_yum_package_install(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "yum repolist && echo SUCCESS", "\r\nSUCCESS\r\n", 60)
        self.ping_pong(connection, "yum search zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 60)
        self.ping_pong(connection, "yum -y install zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 90)
        self.ping_pong(connection, "rpm -q --queryformat '%{NAME}\n' zsh", "\r\nzsh\r\n", 20)
        self.ping_pong(connection, "rpm -e zsh && echo SUCCESS", "\r\nSUCCESS\r\n", 30)
        return self.log
