from valid.valid_testcase import *

class testcase_23_syslog(ValidTestcase):
    def test(self, connection, params):
        rsyslog_md5 = self.get_result(connection, "md5sum /etc/rsyslog.conf | cut -f 1 -d ' '")
        if rsyslog_md5:
            if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
                self.ping_pong(connection, "([ %s = bd4e328df4b59d41979ef7202a05e074 ] || [ %s = 15936b6fe4e8fadcea87b54de495f975 ]) && echo SUCCESS", "\r\nSUCCESS\r\n)")
            elif (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and (params["version"].startswith("6.0") or params["version"].startswith("6.1") or params["version"].startswith("6.2")):
                self.ping_pong(connection, "[ %s = dd356958ca9c4e779f7fac13dde3c1b5 ] && echo SUCCESS", "\r\nSUCCESS\r\n)")
            elif (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("6."):
                self.ping_pong(connection, "[ %s = 8b91b32300134e98ef4aee632ed61e21 ] && echo SUCCESS", "\r\nSUCCESS\r\n)")
            else:
                self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
