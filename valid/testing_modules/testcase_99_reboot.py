from valid.valid_testcase import *
import paramiko
import time

class testcase_99_reboot(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        try:
            self.get_return_value(connection, "reboot")
        except (paramiko.SSHException, EOFError), e:
            self.log.append({"result": "passed", "command": "reboot"})
        time.sleep(30)
        return self.log
