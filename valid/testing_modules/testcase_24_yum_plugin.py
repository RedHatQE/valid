""" This module contains testcase_24_yum_plugin test """
from valid.valid_testcase import ValidTestcase


class testcase_24_yum_plugin(ValidTestcase):
    """
    RHN plugin should be disabled
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*|6.*'}
    tags = ['default']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_return_value(connection, 'grep \'^enabled[[:space:]]*=[[:space:]]*[^0 ]\' /etc/yum/pluginconf.d/rhnplugin.conf', expected_status=1)
        return self.log
