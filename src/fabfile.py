from valigator import TESTS
from fabric.api import env, task

env.key_filename = '/home/mkovacik/.pem/aws-eu-west-1.pem'

@task
def a():
	for test in TESTS:
		print test


