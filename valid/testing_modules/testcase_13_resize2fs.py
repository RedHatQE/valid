from valid.valid_testcase import *

class testcase_13_resize2fs(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("6."):
            self.ping_pong(connection, "[ -b /dev/xvde1 ] && (resize2fs -p /dev/xvde1 15000M && echo SUCCESS) || echo SUCCESS", "[^ ]SUCCESS", 60)
            self.ping_pong(connection, "[ -b /dev/xvda1 ] && (resize2fs -p /dev/xvda1 15000M && echo SUCCESS) || echo SUCCESS", "[^ ]SUCCESS", 60)
            self.get_return_value(connection, "df -h | grep 15G")
        elif (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
            self.get_return_value(connection, "resize2fs -p /dev/sda1 15000M")
            self.get_return_value(connection, "df -h | grep 15G")
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
