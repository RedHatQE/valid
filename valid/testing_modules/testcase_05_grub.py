from valid.valid_testcase import *


class testcase_05_grub(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, "test -h /boot/grub/menu.lst")
        self.ping_pong(connection, "readlink -e /boot/grub/menu.lst", "/boot/grub/grub.conf")
        if params["hwp"]["virtualization"] != "hvm":
            self.get_return_value(connection, "grep '(hd0,0)' /boot/grub/grub.conf", expected_status=1)
        return self.log
