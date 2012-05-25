from zope.interface import implements
from interfaces import IComparable
from fabric.api import run

class Result(object):
	"""A result"""
	implements(IComparable)

	def __cmp__ (self, other):
		raise NotImplementedError

	def __str__(self, other):
		raise NotImplementedError

class SimpleResult(Result):
	"""A result providing a single value"""
	value = None

	def __cmp__(self, other):
		"""compares based on value attribute"""
		return cmp(self.value, other.value)

	def __str__(self):
		"""returns a string representation of self.value"""
		return str(self.value)

class SimpleCommandResult(SimpleResult):
	"""A result that can be obtained running a single E2E command"""
	command = None
	_value = None

	@property
	def value(self):
		"""the value property is a cached result of running the command"""
		if not self._value:
			self._value = run(self.command)
		return self._value


class CastedSimpleCommandResult(SimpleResult):
	"""Provides a casted value running a simple E2E command"""
	value_type = None
	_value = None

	@property
	def value(self):
		if not self._value:
			self._value = self.value_type()
			self._value.from_string(run(self.command))
		return self._value


class DiskSizeActualResult(SimpleCommandResult):
	command = "df -k  `mount | grep ^/dev | awk '{print $1}' ` | awk '{print $2}' | sed -e '/^$/d' |  tail -n+2"
	_value = 0
	# in Kilos
	@property
	def value(self):
		if not self._value:
			for size in run(self.command).split('\n'):
				self._value += int(size)
		return self._value

