from valid.valid_testcase import *


class testcase_28_iptables(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA"):
            self.ping_pong(connection, "service iptables status | grep :22 | grep ACCEPT | wc -l", "\r\n1\r\n")
            self.ping_pong(connection, "service iptables status | grep RELATED,ESTABLISHED | grep ACCEPT | wc -l", "\r\n1\r\n")
            if prod in ["RHEL", "BETA"] and ver.startswith("6."):
                self.ping_pong(connection, "service iptables status | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l", "\r\n2\r\n")
            elif prod in ["RHEL", "BETA"] and ver.startswith("5."):
                self.ping_pong(connection, "service iptables status | grep :631 | grep ACCEPT | wc -l", "\r\n2\r\n")
                self.ping_pong(connection, "service iptables status | grep :5353 | grep ACCEPT | wc -l", "\r\n1\r\n")
                self.ping_pong(connection, "service iptables status | grep -e esp -e ah | grep ACCEPT | wc -l", "\r\n2\r\n")
                self.ping_pong(connection, "service iptables status | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l", "\r\n1\r\n")
            else:
                self.log.append({"result": "skip", "comment": "this test is for RHEL5/RHEL6 only"})
        else:
            self.log.append({"result": "skip", "comment": "this test is for RHEL only"})
        return self.log
