from valid.valid_testcase import *

class testcase_07_libc6_xen_conf(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "test -f /etc/ld.so.conf.d/libc6-xen.conf && echo FAILURE || echo SUCCESS", "[^ ]SUCCESS")
        return self.log
