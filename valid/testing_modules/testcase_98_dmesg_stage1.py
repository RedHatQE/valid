import os
import tempfile
import paramiko
import time
from valid.valid_testcase import *


class testcase_98_dmesg_stage1(ValidTestcase):
    """
    Grab dmesg output
    """
    tags = ['kernel']
    stages = ['stage1']

    def test(self, connection, params):
        self.get_result(connection, 'dmesg > /tmp/dmesg; echo')
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        connection.sftp.get('/tmp/dmesg', tf.name)
        fd = open(tf.name, 'r')
        dmesg = fd.read()
        fd.close()
        os.unlink(tf.name)
        self.log.append({'result': 'passed',
                         'comand': 'get dmesg',
                         'dmesg': dmesg
                         })
        return self.log
