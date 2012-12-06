from valid.valid_testcase import *

class testcase_01_ipv6(ValidTestcase):
    def test(self, connection):
        self.ping_pong(connection, "grep NETWORKING_IPV6=no /etc/sysconfig/network && echo SUCCESS", "[^ ]SUCCESS")
        return self.log
