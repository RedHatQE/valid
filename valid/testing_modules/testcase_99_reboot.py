from valid.valid_testcase import *
import paramiko
import time


class testcase_99_reboot(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        if (prod in ["RHEL", "BETA"] and ver.startswith("5.")) or prod == "Fedora":
            # Booting the latest kernel for stage2 testing
            self.get_return_value(connection, "sed -i 's,\(default\)=.*$,\1=0,' /boot/grub/menu.lst")
        try:
            self.get_return_value(connection, "reboot", nolog=True)
        except (paramiko.SSHException, EOFError), e:
            self.log.append({"result": "passed", "command": "reboot"})
        time.sleep(30)
        return self.log
