""" This module contains testcase_20_auditd test """
from valid.valid_testcase import ValidTestcase


class testcase_20_auditd(ValidTestcase):
    """
    Check auditd:
    - service should be on
    - config files shoud have specified checksums
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': r'5\..*|6\..*|7\..*'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        if params['version'].startswith('6.'):
            auditd_rules_checksum = 'f9869e1191838c461f5b9051c78a638d'
            if params['version'] in ['6.0', '6.1']:
                auditd_checksum = '612ddf28c3916530d47ef56a1b1ed1ed'
                auditd_sysconf_checksum = '123beb3a97a32d96eba4f11509e39da2'
            else:
                auditd_checksum = 'e1886162554c18906df2ecd258aa4794'
                auditd_sysconf_checksum = 'd4d43637708e30418c30003e212f76fc'
            self.ping_pong(connection, 'md5sum /etc/sysconfig/auditd  | cut -f 1 -d \' \'', auditd_sysconf_checksum)
        elif params['version'].startswith('5.'):
            auditd_rules_checksum = 'f9869e1191838c461f5b9051c78a638d'
            auditd_checksum = '612ddf28c3916530d47ef56a1b1ed1ed'
            auditd_sysconf_checksum = '123beb3a97a32d96eba4f11509e39da2'
            self.ping_pong(connection, 'md5sum /etc/sysconfig/auditd  | cut -f 1 -d \' \'', auditd_sysconf_checksum)
        elif params['version'].startswith('7.'):
            auditd_checksum = 'e1886162554c18906df2ecd258aa4794'
            auditd_rules_checksum = 'd5985c09d6c150e433362eca9d59e8fe'
        self.ping_pong(connection, 'md5sum /etc/audit/auditd.conf | cut -f 1 -d \' \'', auditd_checksum)
        self.ping_pong(connection, 'md5sum /etc/audit/audit.rules | cut -f 1 -d \' \'', auditd_rules_checksum)
        return self.log
