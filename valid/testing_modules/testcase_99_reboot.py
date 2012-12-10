from valid.valid_testcase import *

class testcase_99_reboot(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "reboot & echo SUCCESS", "\r\nSUCCESS\r\n")
        return self.log
