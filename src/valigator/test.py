# import boto 
# ec2conn = boto.connect_ec2() 
# from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping 
# map = BlockDeviceMapping() 
# sdb1 = BlockDeviceType() 
# sdc1 = BlockDeviceType() 
# sdd1 = BlockDeviceType() 
# sde1 = BlockDeviceType() 
# sdb1.ephemeral_name = 'ephemeral0' 
# sdc1.ephemeral_name = 'ephemeral1' 
# sdd1.ephemeral_name = 'ephemeral2' 
# sde1.ephemeral_name = 'ephemeral3' 
# map['/dev/sdb1'] = sdb1 
# map['/dev/sdc1'] = sdc1 
# map['/dev/sdd1'] = sdd1 
# map['/dev/sde1'] = sde1 
# img = ec2conn.get_all_images(image_ids=['ami-f61dfd9f'])[0] 
# img.run(key_name='id_bv-keypair', instance_type='c1.xlarge', block_device_map=map) 
from zope.interface import implements
from fabric.tasks import Task

class Test(Task):
	"""Test objects have got an expected and actual result attributes and
	determine their bool value by comparing the expected and actual result"""
	import interfaces
	implements(interfaces.ITest)

	name = "Test"
	actual_result = None
	expected_result = None
	begin_timestamp = None
	end_timestamp = None

	def __bool__(self):
		"""returns the comparison of self.expected_result and
		   self.actual_result"""
		return self.expected_result == self.actual_result

	__nonzero__ = __bool__

	def run(self):
		""" atm just print self """
		# calls str(self) -> bool(self) -> compares actual and expected result
		import time
		self.start_timestamp = time.time()
		print self
		self.end_timestamp = time.time()

	def __str__(self):
		return "<Test: %s; expected result: %s; actual result: %s; passed: %s>" % (self.name, self.expected_result, self.actual_result, bool(self))

