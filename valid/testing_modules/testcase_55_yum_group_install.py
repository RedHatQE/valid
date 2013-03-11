from valid.valid_testcase import *


class testcase_55_yum_group_install(ValidTestcase):
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        self.get_return_value(connection, "yum -y groupinstall 'Development tools'", 600)
        return self.log
