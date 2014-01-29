""" This module contains testcase_28_iptables test """
from valid.valid_testcase import ValidTestcase


class testcase_28_iptables(ValidTestcase):
    """
    Check default iptables setup
    Note that in rhel6.5 iptables are disabled by default and it should be no pre-loaded rules
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA'}
    not_applicable = {'product': '(?i)RHEL|BETA', 'version': r'6.5|7\..*'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        ver = params['version']
        if ver == '6.5':
            # check that there are no pre-loaded rules
            # pylint: disable=C0301
            self.ping_pong(connection, r'iptables -L -n | egrep -v "^Chain .* \(policy ACCEPT\)$|^target.*prot.*opt.*source.*destination|^$" && echo "FAILED" || echo "SUCCESS"',
                           '\r\nSUCCESS\r\n')
        else:
            self.ping_pong(connection, 'iptables -L -n | grep :22 | grep ACCEPT | wc -l', '\r\n1\r\n')
            self.ping_pong(connection, 'iptables -L -n | grep RELATED,ESTABLISHED | grep ACCEPT | wc -l', '\r\n1\r\n')
            if ver.startswith('6.'):
                self.ping_pong(connection, 'iptables -L -n | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l', '\r\n2\r\n')
            elif ver.startswith('5.'):
                self.ping_pong(connection, 'iptables -L -n | grep :631 | grep ACCEPT | wc -l', '\r\n2\r\n')
                self.ping_pong(connection, 'iptables -L -n | grep :5353 | grep ACCEPT | wc -l', '\r\n1\r\n')
                self.ping_pong(connection, 'iptables -L -n | grep -e esp -e ah | grep ACCEPT | wc -l', '\r\n2\r\n')
                self.ping_pong(connection, 'iptables -L -n | grep REJECT | grep all | grep 0.0.0.0/0 | grep icmp-host-prohibited | wc -l', '\r\n1\r\n')
        return self.log
