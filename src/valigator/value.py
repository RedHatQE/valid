
class REValue(object):
	expression = None
	def __eq__ (self, other):
		return self.expression.match(str(other)) != None
	def __str__ (self):
		return "<revalue %r>" % self.expression.pattern

class RetCodeValue(object):
	"""Good for checking return values of a fabric run() command
	   By default, the return_code is set to 0 and a command success "is
	   expected".
	"""
	_failed = False
	return_code = 0
	expected_output = None

	@property
	def succeeded(self):
		return not self.failed

	@succeeded.setter
	def succeeded(self, other):
		self.failed = not other

	@property
	def failed(self):
		return self._failed

	@failed.setter
	def failed(self, other):
		self._failed = bool(other)

	def __eq__ (self, other):
		"""compares self with other forgetting the output
		:param other: as returned by fabric.api.run()
		:type other: string
		:returns True/False
		"""
		ret = True
		try:
			ret &= self.failed == other.failed
			ret &= self.return_code == other.return_code
		except AttributeError:
			return False
		if self.expected_output != None:
			ret &= str(self.expected_result) == str(other)
		return ret

	def __str__(self):
		return "<RetCodeValue return_code %s, failed %s>" % (self.return_code, self.failed)
