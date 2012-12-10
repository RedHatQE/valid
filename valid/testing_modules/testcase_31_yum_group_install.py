from valid.valid_testcase import *

class testcase_31_yum_group_install(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "yum -y groupinstall 'Development tools' && echo SUCCESS", "\r\nSUCCESS\r\n", 600)
        return self.log
