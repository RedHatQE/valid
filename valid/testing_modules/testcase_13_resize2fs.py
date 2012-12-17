from valid.valid_testcase import *


class testcase_13_resize2fs(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if params["hwp"]["virtualization"] != "hvm":
            if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("6."):
                self.get_return_value(connection, "if [ -b /dev/xvde1 ]; then resize2fs -p /dev/xvde1 15000M ; else resize2fs -p /dev/xvda1 15000M; fi", 90)
                self.get_return_value(connection, "df -h | grep 15G")
            elif (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
                self.get_return_value(connection, "resize2fs -p /dev/sda1 15000M", 90)
                self.get_return_value(connection, "df -h | grep 15G")
            else:
                self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        else:
            self.log.append({"result": "passed", "comment": "resize2fs is not applicable for hvm instances"})
        return self.log
