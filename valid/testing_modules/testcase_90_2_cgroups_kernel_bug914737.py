import os
import paramiko
import time
from valid.valid_testcase import *


class testcase_90_2_cgroups_kernel_bug914737(ValidTestcase):
    stages = ["stage1"]
    tags = ["kernel"]

    def test(self, connection, params):
        self.get_return_value(connection, "yum -y install libcgroup-tools", 240)
        connection.sftp.put("/usr/share/valid/data/memory_harvester.py","/root/memory_harvester.py")
        for i in range(10):
            # Creating cpu and memory cgroups
            self.get_return_value(connection, "cgcreate -g cpu:/Group%i" % i)
            self.get_return_value(connection, "cgcreate -g memory:/Group%i" % i)
            self.get_return_value(connection, "cgset -r memory.limit_in_bytes=%i /Group%i" % (i * 100 * 1024 * 1024, i))
            self.get_return_value(connection, "cgset -r cpu.shares=%i /Group%i" % (16384 / (2 ** i), i))
        try:
            self.get_result(connection, "for i in `seq 0 9 `; do cgexec -g cpu:/Group$i -g memory:/Group$i python /root/memory_harvester.py $((i * 1000000)) & echo $i ; done")
            time.sleep(30)
            self.get_return_value(connection, "id")
            self.get_return_value(connection, "killall python ||:")
        except:
            self.log.append({"result": "failed", "command": "bug reproducer succeeded"})
        return self.log
