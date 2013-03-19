from valid.valid_testcase import *


class testcase_22_gpg_keys(ValidTestcase):
    """
    Check that specified gpg keys are installed
    """

    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*"}
    tags = ["default"]

    def test(self, connection, params):
        self.ping_pong(connection, "grep '^gpgcheck=' /etc/yum.repos.d/redhat-*.repo | cut -d\= -f2 | sort -uf | tr -d ' '", "\r\n1\r\n")
        if params["product"].upper() == "BETA":
            self.ping_pong(connection, "rpm -qa gpg-pubkey* | wc -l", "\r\n3\r\n", 10)
        else:
            self.ping_pong(connection, "rpm -qa gpg-pubkey* | wc -l", "\r\n2\r\n", 10)
        self.get_return_value(connection, "rpm -q gpg-pubkey-2fa658e0-45700c69", 30)
        if params["version"].startswith("6."):
            self.get_return_value(connection, "rpm -q gpg-pubkey-fd431d51-4ae0493b", 30)
        elif params["version"].startswith("5."):
            self.get_return_value(connection, "rpm -q gpg-pubkey-37017186-45761324", 30)
        return self.log
