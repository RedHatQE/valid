from valid.valid_testcase import *

class testcase_05_grub(ValidTestcase):
    def test(self, connection, params):
        self.ping_pong(connection, "test -h /boot/grub/menu.lst && echo SUCCESS", "[^ ]SUCCESS")
        self.ping_pong(connection, "readlink -e /boot/grub/menu.lst", "/boot/grub/grub.conf")
        self.ping_pong(connection, "grep '(hd0,0)' /boot/grub/grub.conf && echo FAILURE || echo SUCCESS", "[^ ]SUCCESS")
        return self.log
