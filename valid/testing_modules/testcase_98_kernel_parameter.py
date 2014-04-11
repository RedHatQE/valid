""" This module contains testcase_98_kernel_parameter test """
import os
import paramiko
import time
from valid.valid_testcase import ValidTestcase


class testcase_98_kernel_parameter(ValidTestcase):
    """
    Add specific kernel parameters
    """

    tags = []
    stages = ['stage0']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']
        if 'kernelparams' in params:
            self.get_return_value(connection, 'sed -i \'s,\\(kernel .*$\\),\\1 %s,\' /boot/grub/grub.conf' % params['kernelparams'])
            self.get_return_value(connection, 'nohup sleep 1s && nohup reboot &')
            time.sleep(30)
        else:
            self.log.append({'result': 'skip',
                             'comment': 'no kernelparam was provided'})
        return self.log
