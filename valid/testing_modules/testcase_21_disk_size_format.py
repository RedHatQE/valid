from valid.valid_testcase import *

class testcase_21_disk_size_format(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        disks = self.get_result(connection,  "mount | grep '^/dev' | awk '{print $1}'")
        if disks:
            mpoint = self.match(connection,  "echo '###' ;mount | grep '^%s' | awk '{print $3}'; echo '###'" % disks[0], re.compile(".*\r\n###\r\n(.*)\r\n###\r\n.*", re.DOTALL))
            fs = self.match(connection,  "echo '###' ;mount | grep '^%s' | awk '{print $5}'; echo '###'" % disks[0], re.compile(".*\r\n###\r\n(.*)\r\n###\r\n.*", re.DOTALL))
            if mpoint and fs:
                for disk in disks[0].split():
                    self.ping_pong(connection, "[ `df -k %s | awk '{ print $2 }' | tail -n 1` -gt 3937219 ] && echo SUCCESS" % disk, "\r\nSUCCESS\r\n")
                    if mpoint[0]=='/' and ((params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("6.")):
                        self.ping_pong(connection, "[ %s = ext4 ] && echo SUCCESS"  % fs[0], "\r\nSUCCESS\r\n")
                    else:
                        self.ping_pong(connection, "[ %s = ext3 ] && echo SUCCESS" % fs[0], "\r\nSUCCESS\r\n")
        return self.log
