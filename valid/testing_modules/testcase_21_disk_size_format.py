from valid.valid_testcase import *


class testcase_21_disk_size_format(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        disks = self.get_result(connection, "mount | grep '^/dev' | awk '{print $1}'")
        if disks:
            for disk in disks.split():
                mpoint = self.match(connection, "echo '###' ;mount | grep '^%s' | awk '{print $3}'; echo '###'" % disk, re.compile(".*\r\n###\r\n(.*)\r\n###\r\n.*", re.DOTALL))
                fs = self.match(connection, "echo '###' ;mount | grep '^%s' | awk '{print $5}'; echo '###'" % disk, re.compile(".*\r\n###\r\n(.*)\r\n###\r\n.*", re.DOTALL))
                if mpoint and fs:
                    self.get_return_value(connection, "[ `df -k %s | awk '{ print $2 }' | tail -n 1` -gt 3937219 ]" % disk)
                    if mpoint[0] == '/' and ((params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5.")):
                        self.get_return_value(connection, "[ %s = ext3 ]" % fs[0])
                    else:
                        self.get_return_value(connection, "[ %s = ext4 ]" % fs[0])
        return self.log
