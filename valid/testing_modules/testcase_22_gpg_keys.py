from valid.valid_testcase import *

class testcase_22_gpg_keys(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "grep '^gpgcheck=' /etc/yum.repos.d/redhat-*.repo | cut -d\= -f2 | sort -uf | tr -d ' '", "\r\n1\r\n")
        if params["product"].upper() == "BETA":
            self.ping_pong(connection, "rpm -qa gpg-pubkey* | wc -l", "\r\n3\r\n", 10)
        else:
            self.ping_pong(connection, "rpm -qa gpg-pubkey* | wc -l", "\r\n2\r\n", 10)
        self.ping_pong(connection, "rpm -q gpg-pubkey-2fa658e0-45700c69 && echo SUCCESS", "\r\nSUCCESS\r\n")
        if params["version"].startswith("6."):
            self.ping_pong(connection, "rpm -q gpg-pubkey-fd431d51-4ae0493b && echo SUCCESS", "\r\nSUCCESS\r\n")
        elif params["version"].startswith("5."):
            self.ping_pong(connection, "rpm -q gpg-pubkey-37017186-45761324 && echo SUCCESS", "\r\nSUCCESS\r\n")
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
