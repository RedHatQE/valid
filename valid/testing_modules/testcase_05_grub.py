from valid.valid_testcase import *


class testcase_05_grub(ValidTestcase):
    """
    Check grub config:
    - /boot/grub/menu.lst exists
    - /boot/grub/menu.lst is symlink for /boot/grub/grub.conf
    - hard drive is not (hd0,0) for paravirtual
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*|6.*'}
    tags = ['default']

    def test(self, connection, params):
        self.get_return_value(connection, 'test -h /boot/grub/menu.lst')
        self.ping_pong(connection, 'readlink -e /boot/grub/menu.lst', '/boot/grub/grub.conf')
        if params['virtualization'] != 'hvm':
            self.get_return_value(connection, 'grep \'(hd0,0)\' /boot/grub/grub.conf', expected_status=1)
        return self.log
