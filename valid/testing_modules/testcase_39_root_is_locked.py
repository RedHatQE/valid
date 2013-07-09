import os
import tempfile
import paramiko
import time
from valid.valid_testcase import *


class testcase_39_root_is_locked(ValidTestcase):
    """
    Check root password
    """
    tags = ['default']
    stages = ['stage1']

    def test(self, connection, params):
        # Root account should be locked
        self.get_return_value(connection, 'egrep "^root:(\!\!|\*|x|locked):" /etc/shadow')
        return self.log
