import os
import tempfile
import paramiko
import time
from valid.valid_testcase import *


class testcase_40_selinux_context(ValidTestcase):
    """
    Check selinux context for files
    """
    tags = ['default']
    stages = ['stage1']

    def test(self, connection, params):
        # Check selinux context for /etc/{passwd,group}
        self.get_return_value(connection, 'ls -lZ /etc/passwd | grep "system_u:object_r:etc_t"')
        self.get_return_value(connection, 'ls -lZ /etc/group | grep "system_u:object_r:etc_t"')
        return self.log
