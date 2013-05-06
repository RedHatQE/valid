import os
import tempfile
import paramiko
import time
from valid.valid_testcase import *


class testcase_38_rclocal_checksum(ValidTestcase):
    """
    Grab dmesg output
    """
    tags = ['kernel']
    stages = ['stage1']

    def test(self, connection, params):
        self.get_result(connection, '[ -f /etc/rc.d/rc.local ] && md5sum /etc/rc.d/rc.local || echo "no rc.local"')
        return self.log
