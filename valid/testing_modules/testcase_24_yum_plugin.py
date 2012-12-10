from valid.valid_testcase import *

class testcase_24_yum_plugin(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "grep '^enabled[[:space:]]*=[[:space:]]*[^0 ]' /etc/yum/pluginconf.d/rhnplugin.conf || echo SUCCESS", "\r\nSUCCESS\r\n")
        return self.log
