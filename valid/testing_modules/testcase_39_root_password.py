import os
import tempfile
import paramiko
import time
from valid.valid_testcase import *


class testcase_39_root_password(ValidTestcase):
    """
    Check root password
    """
    tags = ['default']
    stages = ['stage1']

    def test(self, connection, params):
        # Root password shouldn't be empty
        self.get_return_value(connection, 'grep "^root::" /etc/shadow', expected_status=1)
        return self.log
