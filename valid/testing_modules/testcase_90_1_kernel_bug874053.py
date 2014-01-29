""" This module contains testcase_90_1_kernel_bug874053 test """
import time
from valid.valid_testcase import ValidTestcase


class testcase_90_1_kernel_bug874053(ValidTestcase):
    """
    Reproducer for kernel bug 874053
    """
    stages = ['stage1']
    tags = ['kernel']

    def test(self, connection, params):
        """ Perform test """

        if len(params['bmap']) != 8:
            self.log.append({'result': 'skip',
                             'comment': 'Inappropriate bmap'
                             })
            return self.log
        if (params['product'].upper() == 'RHEL' or params['product'].upper() == 'BETA') and params['version'].startswith('6.'):
            # Will assume EL6 device mapping
            devlist = ['xvdf', 'xvdg', 'xvdh', 'xvdi', 'xvdj', 'xvdk', 'xvdl']
        elif (params['product'].upper() == 'RHEL' or params['product'].upper() == 'BETA') and params['version'].startswith('5.'):
            # Will assume EL5 device mapping
            devlist = ['sdb', 'sdc', 'sdd', 'sde', 'sdf', 'sdg', 'sdh']
        else:
            # Will assume Fedora device mapping
            devlist = ['xvdb', 'xvdc', 'xvdd', 'xvde', 'xvdf', 'xvdg', 'xvdh']

        for dev in devlist:
            self.get_result(connection, 'mkfs.ext3 /dev/%s > /dev/null & echo /dev/%s' % (dev, dev))

        # Wait for all mkfs processes
        self.get_result(connection, 'while pidof mkfs.ext3 > /dev/null; do sleep 1; done', 60)

        i = 1
        for dev in devlist:
            self.get_return_value(connection, 'mkdir /mnt/%i' % i)
            self.get_return_value(connection, 'mount /dev/%s /mnt/%i' % (dev, i))
            i += 1

        self.get_return_value(connection, 'yum -y install gcc', 240)
        connection.sftp.put('/usr/share/valid/data/bug874053.c', '/root/fork.c')
        self.get_return_value(connection, 'gcc /root/fork.c')
        self.get_return_value(connection, 'taskset -c 0 ./a.out &')
        time.sleep(5)
        # pylint: disable=C0301,W0702
        try:
            self.get_result(connection, 'for i in `seq 1 7`; do taskset -c $i dd if=/dev/zero of=/mnt/$i/testfile bs=10M count=10000 oflag=direct & echo $i ; done')
            time.sleep(10)
            self.get_return_value(connection, 'id')
            self.get_return_value(connection, 'killall dd ||:')
            self.get_return_value(connection, 'killall a.out ||:')
            for i in range(1, 8):
                self.get_return_value(connection, 'rm -f /mnt/%i/testfile' % i, 30)
                self.get_return_value(connection, 'cp -a /bin/bash /mnt/%i/' % i)
                self.get_result(connection, 'md5sum /bin/bash')
                self.get_result(connection, 'md5sum /mnt/%i/bash' % i)
                self.get_return_value(connection, 'rm -f /mnt/%i/bash' % i)
                self.get_return_value(connection, 'umount /mnt/%i' % i)
        except:
            self.log.append({'result': 'failed', 'command': 'bug reproducer succeeded'})
        return self.log
