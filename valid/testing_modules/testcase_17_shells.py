from valid.valid_testcase import *


class testcase_17_shells(ValidTestcase):
    """
    Check for bash/nologin shells in /etc/shells
    """
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        self.get_return_value(connection, "grep 'bin/bash$' /etc/shells")
        self.get_return_value(connection, "grep 'bin/nologin$' /etc/shells")
        return self.log
