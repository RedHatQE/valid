from zope.interface import Interface

class IOSVersionSwitch(Interface):
	"""I provide a os_version_switch method"""
	def os_version_switch(version):
		"""I determine my behavior by os version"""

class IHWProfileSwitch(Interface):
	"""I provide a hw_profile_switch method"""
	def hw_profile_switch(profile):
		"""I determine my behavior by hw profile"""

class IComparable(Interface):
	"""I provide a __cmp__ method"""
	def __cmp__(other):
		"""I'm able to compare myself with other"""

class ITest(Interface):
	"""I provide a __nonzero__/__bool__ methods for you to be able to tell
	   whether I passed or not"""
	def __bool__():
		"""If I'm True, I passed"""
	def __nonzero__():
		"""If I'm nonzero, I passed"""

class IFromString(Interface):
	"""I provide a from_string method"""

	def from_string(string):
		"""I reset myself from the string"""

