from valigator.ec2.test import Test
from valigator.factories import Factory as baseFactory
from valigator.result import SimpleResult
from zope.interface import implements
from valigator.ec2.interfaces import IInstanceSwitch


class OSVersionTest(Test):
	name = "ec2.OSVersionTest"
	def __init__(self):
		from valigator.ec2.results import ExpectedOSVersionResult
		from valigator.result import CastedSimpleCommandResult
		from valigator.osversion import OSVersion
		self.expected_result = ExpectedOSVersionResult()
		self.actual_result = CastedSimpleCommandResult()
		self.actual_result.value_type = OSVersion
		self.actual_result.command = "cat /etc/redhat-release | awk '{print $7}'"


class Factory(baseFactory):
	def get_test(self):
		return OSVersionTest()


class ExpectedOSVersionResult(SimpleResult):
	"""Depends on an instance"""
	implements(IInstanceSwitch)
	def instance_switch(self, instance):
		"""sets self.value to the expected instance os version"""
		from valigator.osversion import OSVersion
		aVersion = OSVersion()
		aVersion.from_string(instance.version)
		self.value = aVersion
