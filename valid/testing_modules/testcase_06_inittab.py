from valid.valid_testcase import *


class testcase_06_inittab(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "grep '^id:' /etc/inittab", "id:3:initdefault")
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
            self.ping_pong(connection, "grep '^si:' /etc/inittab", "si::sysinit:/etc/rc.d/rc.sysinit")
        return self.log
