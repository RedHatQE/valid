from valid.valid_testcase import *


class testcase_15_rhel_version(ValidTestcase):
    """
    Check redhat-release version
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA'}
    tags = ['default']

    def test(self, connection, params):
        rhelv = self.match(connection, 'rpm -q --qf \'%{RELEASE}\n\' --whatprovides redhat-release', re.compile('.*\r\n([0-9]\.[0-9]+\..*)\r\n.*', re.DOTALL))
        if rhelv:
            self.get_return_value(connection, '[ \'%s\' = \'%s\' ]' % (params['version'], rhelv[0][:len(params['version'])]))
        return self.log
