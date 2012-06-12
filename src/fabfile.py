from fabric.api import env, task, run, settings, execute


env.key_filename = ['/home/mkovacik/.pem/aws-us-east-1.pem']
env.user = 'root'



env.timeout = 5
env.connection_attempts = 12

# TESTS.append(valigator.ec2.tests.OSVersionTest())

import valigator.ec2
from valigator import TESTS

@task
def validate():
	for test in TESTS:
		execute(test)

