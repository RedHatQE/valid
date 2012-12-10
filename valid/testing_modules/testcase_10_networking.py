from valid.valid_testcase import *

class testcase_10_networking(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
    	self.ping_pong(connection, "grep '^NETWORKING=yes' /etc/sysconfig/network && echo SUCCESS", "[^ ]SUCCESS")
    	self.ping_pong(connection, "grep '^DEVICE=eth0' /etc/sysconfig/network-scripts/ifcfg-eth0 && echo SUCCESS", "[^ ]SUCCESS")
        return self.log
