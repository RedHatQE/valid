import os
import paramiko
import time
from valid.valid_testcase import *


class testcase_98_kernel_upgrade_pre(ValidTestcase):
    tags = ["kernel"]
    stages = ["stage0"]

    def test(self, connection, params):
        if "kernelpkg" in params:
            kernelfiles = ""
            if type(params["kernelpkg"]) == str:
                pkgs_files = [params["kernelpkg"]]
            else:
                pkgs_files = params["kernelpkg"]
            for pkg in pkgs_files:
                pkgbase = os.path.basename(pkg)
                connection.sftp.put(pkg,"/tmp/%s" % pkgbase)
                kernelfiles += "/tmp/%s " % pkgbase
                self.get_return_value(connection, "ls -l /tmp/%s" % pkgbase)
            self.get_return_value(connection, "yum -y install %s" % kernelfiles, 300)
        else:
            # doing upgrade from repo
            self.get_return_value(connection, "yum -y install kernel", 300)
        kernel_updated = self.get_return_value(connection, "[ $(rpm -qa kernel | wc -l) -gt 1 ]", nolog=True)
        if kernel_updated == 0:
            # removing old kernel - no way to boot it on EC2 anyway :-)
            self.get_return_value(connection, "rpm -e kernel-`uname -r`", 30)
            try:
                self.get_return_value(connection, "reboot", nolog=True)
            except (paramiko.SSHException, EOFError), e:
                self.log.append({"result": "passed", "command": "reboot"})
            time.sleep(30)
        else:
            self.log.append({
                    "result": "skip",
                    "comment": "no kernel upgrade was done"
                    })
        return self.log
