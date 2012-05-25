import interfaces
from zope.interface import implements

class OSVersion(object):
	"""An OS version object"""
	# implements(interfaces.IComparable)
	# implements(interfaces.IFromString)

	major = None
	minor = None

	def from_string(self, strversion):
		parts = str(strversion).split('.')
		self.major = int(parts[0])
		self.minor = int(parts[1])

	def __cmp__(self, other):
		if self.major < other.major:
			return -1
		if self.major > other.major:
			return 1
		# self.major == other.major if reached here
		if self.minor < other.minor:
			return -1
		if self.minor > other.minor:
			return 1
		# both minors and majors equal
		return 0

	def __str__(self):
		return "%s.%s" % (self.major, self.minor)


