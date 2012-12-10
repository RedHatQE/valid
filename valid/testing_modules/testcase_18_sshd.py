from valid.valid_testcase import *

class testcase_18_sshd(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "chkconfig --list sshd | grep '0:off[[:space:]]*1:off[[:space:]]*2:on[[:space:]]*3:on[[:space:]]*4:on[[:space:]]*5:on[[:space:]]*6:off' && echo SUCCESS", "\r\nSUCCESS\r\n")
        self.ping_pong(connection, "service sshd status | grep running && echo SUCCESS", "\r\nSUCCESS\r\n")
        self.ping_pong(connection, "grep 'PasswordAuthentication no' /etc/ssh/sshd_config && echo SUCCESS", "\r\nSUCCESS\r\n")
        return self.log
