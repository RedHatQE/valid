from valid.valid_testcase import *


class testcase_21_disk_size_format(ValidTestcase):
    """
    Check filesystems:
    - / shoud be ext3 on RHEL5, ext4 otherwise
    - other filesystems shoud be always be ext3
    - all filesystems show have at least 4gb of available space (weird)
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        disks = self.get_result(connection, 'mount | grep \'^/dev\' | awk \'{print $1}\'')
        if disks:
            for disk in disks.split():
                mpoint = self.match(connection, 'echo \'###\' ;mount | grep \'^%s\' | awk \'{print $3}\'; echo \'###\'' % disk, re.compile('.*\r\n###\r\n(.*)\r\n###\r\n.*', re.DOTALL))
                fs = self.match(connection, 'echo \'###\' ;mount | grep \'^%s\' | awk \'{print $5}\'; echo \'###\'' % disk, re.compile('.*\r\n###\r\n(.*)\r\n###\r\n.*', re.DOTALL))
                if mpoint and fs:
                    self.get_return_value(connection, '[ `df -k %s | awk \'{ print $2 }\' | tail -n 1` -gt 3937219 ]' % disk)
                    if mpoint[0] == '/' and ((prod == 'RHEL' or prod == 'BETA') and params['version'].startswith('5.')):
                        # ext3 for / in RHEL5
                        self.get_return_value(connection, '[ %s = ext3 ]' % fs[0])
                    elif mpoint[0] == '/' and ((prod == 'RHEL' or prod == 'BETA') and params['version'].startswith('7.')):
                        # xfs for RHEL7
                        self.get_return_value(connection, '[ %s = xfs ]' % fs[0])
                    elif mpoint[0] == '/':
                        # ext4 for / in other OSes
                        self.get_return_value(connection, '[ %s = ext4 ]' % fs[0])
                    elif mpoint[0] != '/':
                        # ext3 for all other FS in other OSes
                        self.get_return_value(connection, '[ %s = ext3 ]' % fs[0])
        return self.log
