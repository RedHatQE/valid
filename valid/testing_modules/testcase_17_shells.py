from valid.valid_testcase import *


class testcase_17_shells(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "grep 'bin/bash$' /etc/shells")
        self.get_return_value(connection, "grep 'bin/nologin$' /etc/shells")
        return self.log
