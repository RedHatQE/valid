import valigator.test
from fabric.api import env, abort
from valigator.ec2.interfaces import IInstanceSwitch
from valigator.ec2 import INSTANCES
from fabric.utils import puts

class Test(valigator.test.Test):
	def run(self):
		# will check for an instance switch hook presence
		# and call the hook if so
		if not INSTANCES.has_key(env.host_string):
			abort ("""
 Running this test requires an ec2 instance
 started by the task: valigator.ec2.get_hosts just
 before having executed this test"""
					)
		import time
		if IInstanceSwitch.providedBy(self.expected_result):
			self.expected_result.instance_switch(INSTANCES[env.host_string])
		if IInstanceSwitch.providedBy(self.actual_result):
			self.actual_result.instance_switch(INSTANCES[env.host_string])
		self.start_timestamp = time.time()
		puts(self)
		self.end_timestamp = time.time()
