""" This module contains testcase_90_2_cgroups_kernel_bug914737 test """
import time
from valid.valid_testcase import ValidTestcase


class testcase_90_3_bug1074660(ValidTestcase):
    """
    Reproducer for kernel bug 1074660
    """
    stages = ['stage1']
    tags = []

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version'].upper()
        self.get_return_value(connection, 'yum -y install gcc-c++ wget', 300)
        self.get_return_value(connection, 'wget http://www.la-samhna.de/samhain/samhain_signed-2.8.6.tar.gz', 300)
        self.get_return_value(connection, 'tar -zxvf samhain_signed-2.8.6.tar.gz', 10)
        self.get_return_value(connection, 'tar -zxvf samhain-2.8.6.tar.gz', 10)
        self.get_return_value(connection, 'cd samhain-2.8.6 && ./configure && make && make install', 100)
        self.get_return_value(connection, 'samhain -t init', 300)
        self.get_return_value(connection, 'samhain -t check -D', 100)
        try:
            time.sleep(600)
            self.get_return_value(connection, 'id', 30)
        except:
            self.log.append({'result': 'failed', 'command': 'bug reproducer succeeded'})
        return self.log
