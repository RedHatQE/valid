from valid.valid_testcase import *


class testcase_28_iptables(ValidTestcase):
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA"}
    tags = ["default"]

    def test(self, connection, params):
        ver = params["version"]
        self.ping_pong(connection, "iptables -L -n | grep :22 | grep ACCEPT | wc -l", "\r\n1\r\n")
        self.ping_pong(connection, "iptables -L -n | grep RELATED,ESTABLISHED | grep ACCEPT | wc -l", "\r\n1\r\n")
        if ver.startswith("6."):
            self.ping_pong(connection, "iptables -L -n | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l", "\r\n2\r\n")
        elif ver.startswith("5."):
            self.ping_pong(connection, "iptables -L -n | grep :631 | grep ACCEPT | wc -l", "\r\n2\r\n")
            self.ping_pong(connection, "iptables -L -n | grep :5353 | grep ACCEPT | wc -l", "\r\n1\r\n")
            self.ping_pong(connection, "iptables -L -n | grep -e esp -e ah | grep ACCEPT | wc -l", "\r\n2\r\n")
            self.ping_pong(connection, "iptables -L -n | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l", "\r\n1\r\n")
        return self.log
