from valid.valid_testcase import *


class testcase_24_yum_plugin(ValidTestcase):
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*"}

    def test(self, connection, params):
        self.get_return_value(connection, "grep '^enabled[[:space:]]*=[[:space:]]*[^0 ]' /etc/yum/pluginconf.d/rhnplugin.conf", expected_status=1)
        return self.log
