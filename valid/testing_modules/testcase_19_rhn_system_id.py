from valid.valid_testcase import *

class testcase_19_rhn_system_id(ValidTestcase):
    def test(self, connection, params):
        self.ping_pong(connection, "[ ! -f /etc/sysconfig/rhn/systemid ] && echo SUCCESS", "\r\nSUCCESS\r\n")
        return self.log
