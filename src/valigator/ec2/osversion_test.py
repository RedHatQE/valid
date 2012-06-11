from valigator.ec2.test import Test
from valigator.factories import Factory as baseFactory
from valigator.result import SimpleResult
from zope.interface import implements
from valigator.ec2.interfaces import IInstanceSwitch

from valigator.ec2.results import ExpectedOSVersionResult
from valigator.result import CastedSimpleCommandResult
from valigator.osversion import OSVersion

class ExpectedOSVersionResult(SimpleResult):
	"""Depends on an instance"""
	implements(IInstanceSwitch)
	def instance_switch(self, instance):
		"""sets self.value to the expected instance os version"""
		aVersion = OSVersion()
		aVersion.from_string(instance.version)
		self.value = aVersion



class OSVersionTest(Test):
	name = "ec2.OSVersionTest"
	def __init__(self):
		self.expected_result = ExpectedOSVersionResult()
		self.actual_result = CastedSimpleCommandResult()
		self.actual_result.value_type = OSVersion
		self.actual_result.command = "cat /etc/redhat-release | awk '{print $7}'"


class OsVersionTestFactory(baseFactory):
	def get_test(self):
		return OSVersionTest()


class RpmVersionActualResult(CastedSimpleCommandResult):
	value_type = OSVersion
	implements(IInstanceSwitch)
	def instance_switch(self, instance):
		# requires different commands for versions below 6.0
		instance_version = OSVersion()
		instance_version.from_string(instance.version)
		version60 = OSVersion()
		instance_version.major = 6
		instance_version.minor = 0
		if instance_version < version60:
			self.command = "/bin/rpm -q --queryformat '%{RELEASE}\n' redhat-release | cut -d. -f1,2"
		else:
			self.command = "/bin/rpm -q --queryformat '%{RELEASE}\n' redhat-release-server | cut -d. -f1,2"

class RpmOSVersionTest(Test):
	name = "rpm_osversion_test"
	def __init__(self):
		self.expected_result = ExpectedOSVersionResult()
		self.actual_result = RpmVersionActualResult()

class RpmVersionTestFactory(baseFactory):
	def get_test(self):
		return RpmOSVersionTest()

