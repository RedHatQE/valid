from valid.valid_testcase import *


class testcase_06_inittab(ValidTestcase):
    """
    Check default runlevel or systemd target
    """
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        is_systemd = self.get_result(connection, "rpm -q systemd > /dev/null && echo True || echo False")
        if is_systemd == "True":
            self.ping_pong(connection, "readlink -f /etc/systemd/system/default.target", "/lib/systemd/system/multi-user.target")
        else:
            self.ping_pong(connection, "grep '^id:' /etc/inittab", "id:3:initdefault")
            if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
                self.ping_pong(connection, "grep '^si:' /etc/inittab", "si::sysinit:/etc/rc.d/rc.sysinit")
        return self.log
