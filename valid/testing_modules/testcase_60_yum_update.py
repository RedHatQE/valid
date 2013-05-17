from valid.valid_testcase import *


class testcase_60_yum_update(ValidTestcase):
    """
    Test system update with 'yum update'
    """

    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        if prod in ['RHEL', 'BETA'] and ver.startswith('6.') and params['ec2name'] == 't1.micro':
            # Creating swap to workaround mem<1024M issue
            self.ping_pong(connection, 'head -c $((1024*1024*1024)) /dev/zero > /swap && echo SUCCESS', '\r\nSUCCESS\r\n', 150)
            self.get_return_value(connection, 'mkswap /swap', 30)
            self.ping_pong(connection, 'echo \'/swap    swap     swap    defaults     0 0\' >> /etc/fstab && echo SUCCESS', '\r\nSUCCESS\r\n')
            self.get_return_value(connection, 'swapon -a -e', 30)
        self.get_return_value(connection, 'yum -y install kernel', 900)
        # yum -y update || yum -y update because we've seen this in 5.7:
        #    zlib.x86_64 0:1.2.3-7.el5                                
        #    Complete!
        #    [root@ip-10-12-133-111 ~]# echo $?      
        #    1
        #    [root@ip-10-12-133-111 ~]# echo $?      
        self.get_return_value(connection, 'yum -y update || yum -y update', 900)
        return self.log
