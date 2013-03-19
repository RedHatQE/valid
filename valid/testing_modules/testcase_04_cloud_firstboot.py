from valid.valid_testcase import *


class testcase_04_cloud_firstboot(ValidTestcase):
    """
    Check that rh-cloud-firstboot is disabled
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*'}
    tags = ['default']

    def test(self, connection, params):
        self.ping_pong(connection, 'chkconfig --list rh-cloud-firstboot', '3:off')
        self.get_return_value(connection, 'test -f /etc/sysconfig/rh-cloud-firstboot')
        self.ping_pong(connection, 'cat /etc/sysconfig/rh-cloud-firstboot', 'RUN_FIRSTBOOT=NO')
        return self.log
