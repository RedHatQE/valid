from valid.valid_testcase import *


class testcase_03_chkconfig(ValidTestcase):
    """
    Check for several services runnung
    - crond
    - iptables( should be disabled by default in rhel6.5)
    - yum-updatesd (RHEL5 only)
    """
    stages = ['stage1']
    tags = ['default']
    def test(self, connection, params):
        is_systemd = self.get_result(connection, 'rpm -q systemd > /dev/null && echo True || echo False')
        if is_systemd == 'True':
            self.get_return_value(connection, 'systemctl is-active crond.service')
            self.get_return_value(connection, 'systemctl is-active iptables.service')
        else:
            self.ping_pong(connection, 'chkconfig --list crond', '3:on')
            self.ping_pong(connection, 'chkconfig --list iptables', '3:off' if params['version'] == '6.5' else '3:on')
            if (params['product'].upper() == 'RHEL' or params['product'].upper() == 'BETA') and params['version'].startswith('5.'):
                self.ping_pong(connection, 'chkconfig --list yum-updatesd', '3:on')
        return self.log
