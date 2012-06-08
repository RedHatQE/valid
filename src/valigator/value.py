
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

	@property
	def succeeded(self):
		return not self.failed

	@property
	def failed(self):
		return self._failed

	@failed.setter
	def failed(self, other):
		self._failed = bool(other)

	def __eq__ (self, other):
		"""compares self with other forgetting the output"""
		ret = True
		try:
			ret &= self.failed == other.failed
			ret &= self.return_code == other.return_code
		except AttributeError:
			return False
		return ret

	def __str__(self):
		return "<RetCodeValue return_code %s, failed %s>" % (self.return_code, self.failed)
