from valid.valid_testcase import *


class testcase_12_passwd_group(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "grep '^root:x:0:0:root:/root:/bin/bash' /etc/passwd")
        self.get_return_value(connection, "grep '^nobody:x:99:99:Nobody:/:/sbin/nologin' /etc/passwd")
        self.get_return_value(connection, "grep '^sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin' /etc/passwd")
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA"):
            if params["version"].startswith("5.") or params["version"].startswith("6.0") or params["version"].startswith("6.1") or params["version"].startswith("6.2"):
                self.get_return_value(connection, "grep '^root:x:0:root' /etc/group")
                self.get_return_value(connection, "grep '^daemon:x:2:root,bin,daemon' /etc/group")
                self.get_return_value(connection, "grep '^bin:x:1:root,bin,daemon' /etc/group")
            elif params["version"].startswith("6."):
                self.get_return_value(connection, "grep '^root:x:0:' /etc/group")
                self.get_return_value(connection, "grep '^daemon:x:2:bin,daemon' /etc/group")
                self.get_return_value(connection, "grep '^bin:x:1:bin,daemon' /etc/group")
        else:
            self.log.append({"result": "skip", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
