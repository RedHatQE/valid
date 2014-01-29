""" This module contains testcase_98_dmesg_stage1 test """
import os
import tempfile
from valid.valid_testcase import ValidTestcase


class testcase_98_dmesg_stage1(ValidTestcase):
    """
    Grab dmesg output
    """
    tags = ['kernel']
    stages = ['stage1']

    # pylint: disable=W0613
    def test(self, connection, params):
        """ Perform test """

        self.get_result(connection, 'dmesg > /tmp/dmesg; echo')
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.close()
        connection.sftp.get('/tmp/dmesg', tfile.name)
        with open(tfile.name, 'r') as dmesgfile:
            dmesg = dmesgfile.read()
        os.unlink(tfile.name)
        self.log.append({'result': 'passed',
                         'comand': 'get dmesg',
                         'dmesg': dmesg
                         })
        return self.log
