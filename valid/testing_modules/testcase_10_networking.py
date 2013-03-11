from valid.valid_testcase import *


class testcase_10_networking(ValidTestcase):
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        self.get_return_value(connection, "grep '^NETWORKING=yes' /etc/sysconfig/network")
        self.get_return_value(connection, "grep '^DEVICE=eth0' /etc/sysconfig/network-scripts/ifcfg-eth0")
        return self.log
