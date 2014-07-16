""" This module contains testcase_23_syslog test """
from valid.valid_testcase import ValidTestcase


class testcase_23_syslog(ValidTestcase):
    """
    Check /etc/rsyslog.conf checksum
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': 'OS(>=5.5, <7.0)'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        ver = params['version']
        rsyslog_md5 = self.get_result(connection, 'md5sum /etc/rsyslog.conf | cut -f 1 -d \' \'')
        rsyslog_md5_check = []
        if rsyslog_md5:
            if ver.startswith('5.'):
                rsyslog_md5_check = ['bd4e328df4b59d41979ef7202a05e074', '15936b6fe4e8fadcea87b54de495f975']
            elif ver[:3] in ['6.0', '6.1', '6.2']:
                rsyslog_md5_check = ['dd356958ca9c4e779f7fac13dde3c1b5']
            elif ver.startswith('6.'):
                rsyslog_md5_check = ['8b91b32300134e98ef4aee632ed61e21']

        if rsyslog_md5 in rsyslog_md5_check:
            self.log.append({'result': 'passed', 'comment': '/etc/rsyslog.conf md5 matches'})
        else:
            self.log.append({'result': 'failed', 'comment': '/etc/rsyslog.conf md5 differs (%s, should be %s)' % (rsyslog_md5, rsyslog_md5_check)})

        return self.log
