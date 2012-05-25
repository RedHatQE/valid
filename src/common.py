from fabric.api import run, env
from fabric.tasks import Task

class Result(object):
	test = None
	def __str__(self):
		raise NotImplementedError
	def __eq__(self, other):
		raise NotImpementedError


class Test(Task):
	actual_result = None
	expected_result = None
	start_timestamp = None
	end_timestamp = None
	name = None

	def __nonzero__(self):
		return self.expected_result == self.actual_result

	def run(self):
		import time
		self.start_timestamp = time.time()
		# calls str(self) -> bool(self) -> compares actual and expected
		# results
		print self
		self.end_timestamp = time.time()

	def __str__(self):
		return "<Test: %s; expected result: %s; actual result: %s; passed: %s>" % (self.name,
				self.expected_result, self.actual_result, bool(self))


class VersionExpectedResult(Result):
	def __init__(self, version):
		Result.__init__(self)
		self.version = version
	def __eq__(self, other):
		return str(other) == str(self.version)

	def __str__(self):
		return str(self.version)


class VersionActualResult(Result):
	version=None
	def __eq__(self, other):
		return str(other) == str(self)

	def __str__(self):
		if not self.version:
			self.version = run("cat /etc/redhat-release | awk '{print $7}'")
		return self.version


class RhelVersionTest(Test):
	name = 'RhelVersionTest'
	def __init__(self, version):
		Test.__init__(self)
		self.expected_result = VersionExpectedResult(version)
		self.actual_result = VersionActualResult()
		self.expected_result.test = self
		self.actual_result.test = self


class DiskSizeExpectedResult(Result):
	# in Kilos
	size = 0

	def __init__(self, size):
		Result.__init__(self)
		self.size = size

	def __eq__(self, other):
		try:
			return int(other.size) >= int(self.size)
		except AttributeError:
			return False

	def __str__(self):
		return "size >= %skB" % self.size


class DiskSizeActualResult(Result):
	_mount_cmd = "mount | grep ^/dev | awk '{print $1}'"
	_size_cmd = "df -k %s | awk '{print $2}' | tail -n 1"
	_size = 0
	# in Kilos
	@property
	def size(self):
		if not self._size:
			for partition in run(self._mount_cmd).split('\n'):
				self._size += int(run(self._size_cmd % partition))
		return self._size

	def __eq__(self, other):
		try:
			return int(other.size) <= int(self.size)
		except AttributeError:
			return False

	def __str__(self):
		return "%skB" % self.size


class DiskSizeTest(Test):
	size = 4194304
	name = 'TestDiskSize'

	def __init__(self):
		Test.__init__(self)
		self.expected_result = DiskSizeExpectedResult(self.size)
		self.actual_result = DiskSizeActualResult()
		self.expected_result.test = self
		self.actual_result.test = self

class RootPartFstypeExpectedResult(Result):
	fstype = None

	def __init__(self, fstype):
		Result.__init__(self)
		self.fstype = fstype

	def __eq__(self, other):
		try:
			return self.fstype == other.fstype
		except AttributeError:
			return False

	def __str__(self):
		return "root part fstype: %s" % self.fstype

class RootPartFstypeActualResult(Result):
	_fstype = None
	_command = "mount | grep 'on\ /\ ' | awk '{print $5}'"

	@property
	def fstype(self):
		if not self._fstype:
			self._fstype = run(self._command)
		return self._fstype

	def __eq__(self, other):
		return self.fstype == other.fstype

	def __str__(self):
		return "root part fstype: %s" % self.fstype

class RootPartFstypeTest(Test):
	name = 'RootPartFstypeTest'
	def __init__(self, fstype):
		Test.__init__(self)
		self.expected_result = RootPartFstypeExpectedResult(fstype)
		self.actual_result = RootPartFstypeActualResult()
		self.expected_result.test = self
		self.actual_result.test = self

if __name__ == '__main__':
	raise RuntimeError("to be used through fabric only\nCheck `fab -h'...")

