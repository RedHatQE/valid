from valid.valid_testcase import *

class testcase_01_ipv6(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "grep NETWORKING_IPV6=no /etc/sysconfig/network")
        return self.log
