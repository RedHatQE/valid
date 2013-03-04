import os
import paramiko
import time
from valid.valid_testcase import *


class testcase_98_kernel_upgrade_pre(ValidTestcase):
    stages = ["stage0"]

    def test(self, connection, params):
        if not "kernelpkg" in params:
            self.log.append({
                    "result": "skip",
                    "comment": "No kernel package provided for upgrade"
                    })
            return self.log
        kernelfile = params["kernelpkg"]
        kernelbase = os.path.basename(kernelfile)
        connection.sftp.put(kernelfile,"/tmp/%s" % kernelbase)
        self.get_return_value(connection, "ls -l /tmp/%s" % kernelbase)
        self.get_return_value(connection, "yum -y install /tmp/%s" % kernelbase, 300)
        self.get_return_value(connection, "rpm -e kernel-`uname -r`", 30)
        try:
            self.get_return_value(connection, "reboot", nolog=True)
        except (paramiko.SSHException, EOFError), e:
            self.log.append({"result": "passed", "command": "reboot"})
        time.sleep(30)
        return self.log
