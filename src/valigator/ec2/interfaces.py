from zope.interface import Interface

class  IInstanceSwitch(Interface):
	"""I provide an instance_switch method"""
	def instance_switch(instance):
		"""My behavior is determined by an ec2 instance"""
