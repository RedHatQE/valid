from valid.valid_testcase import *

class testcase_12_passwd_group(ValidTestcase):
    def test(self, connection, params):
    	self.ping_pong(connection, "grep '^root:x:0:0:root:/root:/bin/bash' /etc/passwd && echo SUCCESS", "[^ ]SUCCESS")
    	self.ping_pong(connection, "grep '^nobody:x:99:99:Nobody:/:/sbin/nologin' /etc/passwd && echo SUCCESS", "[^ ]SUCCESS")
    	self.ping_pong(connection, "grep '^sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin' /etc/passwd && echo SUCCESS", "[^ ]SUCCESS")
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA"):
            if params["version"].startswith("5.") or params["version"].startswith("6.0") or params["version"].startswith("6.1") or params["version"].startswith("6.2"):
                self.ping_pong(connection, "grep '^root:x:0:root' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
                self.ping_pong(connection, "grep '^daemon:x:2:root,bin,daemon' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
                self.ping_pong(connection, "grep '^bin:x:1:root,bin,daemon' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
            elif params["version"].startswith("6."):
                self.ping_pong(connection, "grep '^root:x:0:' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
                self.ping_pong(connection, "grep '^daemon:x:2:bin,daemon' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
                self.ping_pong(connection, "grep '^bin:x:1:bin,daemon' /etc/group && echo SUCCESS", "[^ ]SUCCESS")
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
