from valid.valid_testcase import *


class testcase_09_nameserver(ValidTestcase):
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        if prod == "FEDORA" and ver in ["18", "19"]:
            self.get_return_value(connection, "yum -y install /usr/bin/dig", 240)
        self.get_return_value(connection, "dig clock.redhat.com | grep 66.187.233.4")
        return self.log
