
class REValue(object):
	expression = None
	def __eq__ (self, other):
		return self.expression.match(str(other)) != None
	def __str__ (self):
		return "<revalue %r>" % self.expression.pattern


