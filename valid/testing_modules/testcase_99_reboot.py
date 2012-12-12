from valid.valid_testcase import *
import paramiko
import time

class testcase_99_reboot(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if prod in ["RHEL", "BETA"] and ver.startswith("6.") and params["hwp"]["name"]=="t1.micro":
            # Creating swap to workaround mem<1024M issue
            self.get_return_value(connection, "head -c $((1024*1024*1024)) /dev/zero > /swap", 120)
            self.get_return_value(connection, "mkswap /swap", 30)
            self.get_return_value(connection, "echo '/swap    swap     swap    defaults     0 0' >> /etc/fstab")
        elif prod in ["RHEL", "BETA"] and ver.startswith("5."):
            # Booting the latest kernel for stage2 testing
            self.get_return_value(connection, "sed -i 's,\(default\)=.*$,\1=0,' /boot/grub/menu.lst")
        try:
            self.get_return_value(connection, "reboot")
        except (paramiko.SSHException, EOFError), e:
            self.log.append({"result": "passed", "command": "reboot"})
        time.sleep(30)
        return self.log
