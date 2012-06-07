from valigator.ec2.test import Test
from valigator.factories import Factory as baseFactory
from valigator.result import SimpleResult, SimpleCommandResult
from zope.interface import implements
from valigator.ec2.interfaces import IInstanceSwitch

class DiskTypeExpectedResult(SimpleResult):
	implements(IInstanceSwitch)
	def instance_switch(self, instance):
		"""Figure out what file system is an instance expected tho use on
		its rootdisk based on version of the instance"""
		from ..osversion import OSVersion
		v6_x = OSVersion()
		v6_x.from_string('6.0')
		iversion = OSVersion()
		iversion.from_string(str(instance.version))
		if iversion < v6_x:
			self.value = 'ext3'
		else:
			self.value = 'ext4'

class DiskTypeTestFactory(baseFactory):
	def get_test(self):
		test = Test()
		test.name = 'ec2.DiskTypeTest'
		test.expected_result = DiskTypeExpectedResult()
		test.actual_result = SimpleCommandResult()
		test.actual_result.command = "mount | grep ' / ' | awk '{print $5}'"
		return test
