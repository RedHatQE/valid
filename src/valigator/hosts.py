import interfaces
from zope.interface import implements


class Host(object):
	implements(interfaces.IFabricHostString)
	hostname = 'localhost'
	username = 'root'
	def get_host_string(self):
		return "%s" % self.hostname
	def __str__(self):
		return "<hostname: %s username: %s>"
	__repr__ = __str__

