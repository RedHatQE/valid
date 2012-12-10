from valid.valid_testcase import *

class testcase_03_chkconfig(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "chkconfig --list crond", "3:on")
        self.ping_pong(connection, "chkconfig --list iptables", "3:on")
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
            self.ping_pong(connection, "chkconfig --list yum-updatesd", "3:on")
        return self.log
