from zope.interface import implements
import interfaces, test, result
from osversion import OSVersion

FACTORIES = []

class Factory(object):
	"""an import-time hook implementation to fetch all test factories"""
	implements(interfaces.ITestFactory)
	class __metaclass__(type):
		def __init__(cls, name, bases, dict):
			print cls, name, bases
			type.__init__(cls, name, bases, dict)
			# avoid abstract factories
			if cls.__module__ != 'valigator.factories' or cls.__name__ not in ('Factory', 'RetValueCheckFactory'):
				FACTORIES.append((name, cls))
	def get_test(self):
		"""return a test instance"""
		return test.Test()

class RetValueCheckFactory(Factory):
	"""To use, just set a command and test_name.
	   If needed, set return_value as well.
	   Produces a very basic simple-result vs simple-command-result checking
	   focused on return value checks
	"""
	return_code = 0
	failed = False
	command = None
	test_name = None
	def get_test(self):
		from test import Test
		ret = Test()
		ret.name = self.test_name
		from result import SimpleResult
		ret.expected_result = SimpleResult()
		from value import RetCodeValue
		ret.expected_result.value = RetCodeValue()
		ret.expected_result.value.return_code = self.return_code
		ret.expected_result.value.failed = self.failed
		from result import SimpleCommandResult
		if self.failed:
			# in case command failure is expected, switch the setting
			# warn_only to True
			ret.actual_result = SimpleCommandResult(warn_only=True)
		else:
			ret.actual_result = SimpleCommandResult()
		ret.actual_result.command = self.command
		return ret



class CastedFactory(object):
	"""An attribute value type-casting and name-converting factory"""
	instance_type = None
	instance_casted_attributes = {}
	instance_renamed_attributes = {}
	def __call__(self, dict, *args, **kvargs):
		ret = self.instance_type(*args, **kvargs)
		for key in dict.keys():
			if key in self.instance_renamed_attributes:
				# renaming required
				renamed_key = self.instance_renamed_attributes[key]
				if renamed_key in self.instance_casted_attributes:
					# cast accordingly with renaming the attribute
					setattr(ret, renamed_key,
							self.instance_casted_attributes[renamed_key](dict[key]))
				else:
					# just rename, no casting required
					setattr(ret, renamed_key, dict[key])
			else:
				# renaming not required
				if key in self.instance_casted_attributes:
					# casting required
					setattr(ret, key, self.instance_casted_attributes[key](dict[key]))
				else:
					# no attribute manipulation needed, just setting
					setattr(ret, key, dict[key])
		return ret


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
