from valid.valid_testcase import *


class testcase_09_nameserver(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "dig clock.redhat.com | grep 66.187.233.4")
        return self.log
