""" This module contains testcase_13_resize2fs test """
from valid.valid_testcase import ValidTestcase


class testcase_13_resize2fs(ValidTestcase):
    """
    The instances are always created with a 15GB root device (unlike
    the AWS default of 8GB. The point is whether we're able to allocate
    the space. Please note that cloud-init does the resize automatically.
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*|6.*', 'virtualization': '(?!hvm)'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']
        if self.get_return_value(connection, 'rpm -q cloud-init', nolog=True) == 1:
            # cloud-init not installed, resize
            if prod in ['RHEL', 'BETA'] and ver.startswith('6.'):
                self.get_return_value(connection, 'if [ -b /dev/xvde1 ]; then resize2fs -p /dev/xvde1 15000M ; else resize2fs -p /dev/xvda1 15000M; fi', 180)
            elif prod in ['RHEL', 'BETA'] and ver.startswith('5.'):
                self.get_return_value(connection, 'resize2fs -p /dev/sda1 15000M', 180)
        self.get_return_value(connection, 'df -h | grep 15G')
        return self.log
