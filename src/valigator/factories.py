from zope.interface import implements
import interfaces, test, result
from osversion import OSVersion

FACTORIES = []

class Factory(object):
	implements(interfaces.ITestFactory)
	class __metaclass__(type):
		def __init__(cls, name, bases, dict):
			print cls, name, bases
			type.__init__(cls, name, bases, dict)
			FACTORIES.append((name, cls))
	def get_test(self):
		return test.Test()

import ec2

# class OSVersionTestFactory(Factory):
# 	implements(interfaces.IOSVersionSwitch)
# 
# 	version = None
# 
# 	def os_version_switch(self, version):
# 		self.version = version
# 
# 	def get_test(self):
# 		aTest = test.Test()
# 		aTest.name = "OsVersionTest"
# 		aTest.expected_result = result.SimpleResult()
# 		aTest.expected_result.value = self.version
# 		aTest.actual_result = result.CastedSimpleCommandResult()
# 		aTest.actual_result.value_type = OSVersion
# 		aTest.actual_result.command = "cat /etc/redhat-release | awk '{print $7}'"
# 		return aTest
# 
# class DiskSizeTestFactory(Factory):
# 	def get_test(self):
# 		aTest = test.Test()
# 		aTest.name = "OsVersionTest"
# 		aTest.expected_result = result.SimpleResult()
# 		aTest.expected_result.value = 4194304
# 		aTest.actual_result = result.DiskSizeActualResult()
# 		def customBool(a, b):
# 			return a.value <= b.value
# 		aTest.__nonzero__ = customBool
# 		return aTest
