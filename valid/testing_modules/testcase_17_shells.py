from valid.valid_testcase import *

class testcase_17_shells(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "grep 'bin/bash$' /etc/shells && echo SUCCESS", "\r\nSUCCESS\r\n")
        self.ping_pong(connection, "grep 'bin/nologin$' /etc/shells && echo SUCCESS", "\r\nSUCCESS\r\n")
        return self.log
