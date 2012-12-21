from valid.valid_testcase import *


class testcase_23_syslog(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        rsyslog_md5 = self.get_result(connection, "md5sum /etc/rsyslog.conf | cut -f 1 -d ' '")
        if rsyslog_md5:
            if prod in ["RHEL", "BETA"] and ver.startswith("5."):
                self.get_return_value(connection, "([ %s = bd4e328df4b59d41979ef7202a05e074 ] || [ %s = 15936b6fe4e8fadcea87b54de495f975 ])" % (rsyslog_md5, rsyslog_md5))
            elif prod in ["RHEL", "BETA"] and ver[:3] in ["6.0", "6.1", "6.2"]:
                self.get_return_value(connection, "[ %s = dd356958ca9c4e779f7fac13dde3c1b5 ]" % rsyslog_md5)
            elif prod in ["RHEL", "BETA"] and ver.startswith("6."):
                self.get_return_value(connection, "[ %s = 8b91b32300134e98ef4aee632ed61e21 ]" % rsyslog_md5)
            else:
                self.log.append({"result": "skip", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
