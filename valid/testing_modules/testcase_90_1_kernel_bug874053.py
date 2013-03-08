import os
import paramiko
import time
from valid.valid_testcase import *


class testcase_90_1_kernel_bug874053(ValidTestcase):
    stages = ["stage1"]
    tags = ["kernel"]

    def test(self, connection, params):
        if len(params["bmap"]) != 8:
            self.log.append({
                    "result": "skip",
                    "comment": "Inappropriate bmap"
                    })
            return self.log
        # Will assume EL6 device mapping
        for dev in ['f', 'g', 'h', 'i', 'j', 'k', 'l']:
            self.get_return_value(connection, "mkfs.ext3 /dev/xvd%s > /dev/null &" % dev)
        
        # Wait for all mkfs processes    
        self.get_return_value(connection, "while pidof mkfs.ext3 > /dev/null; do sleep 1; done", 120)

        i = 1
        for dev in ['f', 'g', 'h', 'i', 'j', 'k', 'l']:
            self.get_return_value(connection, "mkdir /mnt/%i" % i)
            self.get_return_value(connection, "mount /dev/xvd%s /mnt/%i" % (dev, i))
            i += 1

        self.get_return_value(connection, "yum -y install gcc", 240)
        connection.sftp.put("/usr/share/valid/data/bug874053.c","/root/fork.c")
        self.get_return_value(connection, "gcc /root/fork.c")
        self.get_return_value(connection, "taskset -c 0 ./a.out &")
        time.sleep(5)
        try:
            self.get_result(connection, "for i in `seq 1 7`; do taskset -c $i dd if=/dev/zero of=/mnt/$i/testfile bs=10M count=10000 oflag=direct & echo $i ; done")
            time.sleep(10)
            self.get_return_value(connection, "id")
        except:
            self.log.append({"result": "failed", "command": "bug reproducer succeeded"})
        return self.log
