from valid.valid_testcase import *


class testcase_07_libc6_xen_conf(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "test -f /etc/ld.so.conf.d/libc6-xen.conf", expected_status=1)
        return self.log
