import common
from fabric.api import env, task

env.key_filename = '/home/mkovacik/.pem/aws-eu-west-1.pem'

t1 = common.RhelVersionTest('6.3')
d1 = common.DiskSizeTest()
p1 = common.RootPartFstypeTest('ext4')
