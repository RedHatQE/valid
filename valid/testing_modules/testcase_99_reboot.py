""" This module contains testcase_99_reboot test """
from valid.valid_testcase import ValidTestcase
from paramiko import SSHException
from socket import error as SocketError
import time


class testcase_99_reboot(ValidTestcase):
    """
    Reboot the instance
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']
        self.get_return_value(connection, 'echo \'doing reboot\'')
        if (prod in ['RHEL', 'BETA'] and ver.startswith('5.')) or prod == 'FEDORA':
            # Booting the latest kernel for stage2 testing
            self.get_return_value(connection, r'sed -i "s,\(default\)=.*$,\1=0," /boot/grub/menu.lst')
        self.get_return_value(connection, 'nohup sleep 1s && nohup reboot &')
        time.sleep(30)
        return self.log
