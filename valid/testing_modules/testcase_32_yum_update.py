from valid.valid_testcase import *

class testcase_32_yum_update(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "yum -y update && echo SUCCESS", "\r\nSUCCESS\r\n", 600)
        return self.log
