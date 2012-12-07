from valid.valid_testcase import *

class testcase_16_selinux(ValidTestcase):
    def test(self, connection, params):
        self.ping_pong(connection, "getenforce", "\r\nEnforcing\r\n")
        self.ping_pong(connection, "grep '^SELINUX=enforcing' /etc/sysconfig/selinux && echo SUCCESS", "\r\nSUCCESS\r\n")
        self.ping_pong(connection, "grep '^SELINUXTYPE=targeted' /etc/sysconfig/selinux && echo SUCCESS", "\r\nSUCCESS\r\n")
        self.ping_pong(connection, "setenforce Permissive && getenforce", "\r\nPermissive\r\n")
        self.ping_pong(connection, "setenforce Enforcing && getenforce", "\r\nEnforcing\r\n")
        return self.log
