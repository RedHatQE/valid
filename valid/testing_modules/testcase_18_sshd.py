from valid.valid_testcase import *


class testcase_18_sshd(ValidTestcase):
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        is_systemd = self.get_result(connection, "rpm -q systemd > /dev/null && echo True || echo False")
        if is_systemd == "True":
            self.get_return_value(connection, "systemctl is-active sshd.service")
        else:
            self.get_return_value(connection, "chkconfig --list sshd | grep '0:off[[:space:]]*1:off[[:space:]]*2:on[[:space:]]*3:on[[:space:]]*4:on[[:space:]]*5:on[[:space:]]*6:off'")
            self.get_return_value(connection, "service sshd status | grep running")
        self.get_return_value(connection, "grep 'PasswordAuthentication no' /etc/ssh/sshd_config")
        return self.log
