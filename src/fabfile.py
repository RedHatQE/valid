from fabric.api import env, task, run, settings, execute


env.key_filename = ['/home/mkovacik/.pem/aws-us-east-1.pem']
env.user = 'root'

key_name = 'aws-us-east-1'
ami = 'ami-41d00528'
instance_type = 't1.micro' #{"name":"t1.micro","memory":"600000","cpu":"1","arch":"x86_64"}

ec2_key='AKIAJI4XN4LZAHCZUUAQ'
ec2_secret_key='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'

env.timeout = 5
env.connection_attempts = 12

# TESTS.append(valigator.ec2.tests.OSVersionTest())

import valigator.ec2
from valigator import TESTS

@task
def validate():
	for test in TESTS:
		execute(test)

