from valid.valid_testcase import *

class testcase_32_yum_update(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "yum -y update", 600)
        return self.log
