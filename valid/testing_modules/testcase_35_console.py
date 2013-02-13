from valid.valid_testcase import *


class testcase_35_console(ValidTestcase):
    stages = ["stage1"]
    applicable = {"virtualization": "hvm"}

    def test(self, connection, params):
        self.get_return_value(connection, "grep 'console=ttyS0' /proc/cmdline")
        return self.log
