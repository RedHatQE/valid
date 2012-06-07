#from valigator.hosts iddmport Host
#import time

# class Instance(Host):
# 	image = None
# 	def __init__(self, connection, key_name, ami, instance_type):
# 		import boto
# 		from boto.ec2.blockdevicemapping import BlockDeviceMapping, EBSBlockDeviceType
# 		block_device_map = BlockDeviceMapping()
# 		block_device_map['/dev/sda1'] = EBSBlockDeviceType()
# 		block_device_map['/dev/sda1'].size = 15
# 		reservation = connection.run_instances(ami, instance_type =
# 				instance_type, key_name = key_name, block_device_map =
# 				block_device_map)
# 		self.instance = reservation.instances[0]
# 		# from time to time, instance does not exist at this point
# 		time.sleep(5)
# 		steps = 62
# 		while self.instance.update() != 'running' and steps > 0:
# 			time.sleep(5)
# 			steps -= 1
# 		if steps == 0:
# 			raise RuntimeError("Timeout waiting for %s to run" % self.instance)
# 		self.hostname = self.instance.public_dns_name
# 		self.id = self.instance.id
# 		self.image_id = self.instance.image_id
# 		self.instance_type = self.instance.instance_type
# 		self.architecture = self.instance.architecture

import valigator
from zope.interface import implements
from ..interfaces import IFromString

class Instance(object):
	"""A basic Instance representation"""
	implements(valigator.interfaces.IFabricHostString)
	id = None
	ami = None
	region = None
	hw_type = None
	arch = None
	version = None
	hostname = None
	key_file = None
	username = None

	def get_host_string(self):
		return "%s@%s" % (self.username, self.hostname)

	def __str__(self):
		return "<instance id %s hostname %s, ami %s, region %s, hw_type %s, arch %s, version %s, key_file %s, username %s>" % \
			(self.id, self.hostname, self.ami, self.region, self.hw_type, self.arch, self.version, self.key_file, self.username)

	__repr__ = __str__

	def __eq__ (self, other):
		ret = True
		try:
			ret &= self.id == other.id
			ret &= self.ami == other.ami
			ret &= self.region == other.region
			ret &= self.hw_type == other.hw_type
			ret &= self.arch == other.arch
			ret &= self.version == other.version
			ret &= self.hostname == other.hostname
			ret &= self.key_file == other.key_file
			ret &= self.username == other.username
		except AttributeError:
			return False
		return ret


class JsonInstance(Instance):
	"""Provides some json handling.
	   Here is, what one gets from http://169.254.169.254/latest/dynamic/instance-identity/document:
	   {
	     "kernelId" : "aki-eafa0183",
	     "ramdiskId" : null,
	     "instanceId" : "i-e213dc9b",
	     "billingProducts" : [ "bp-63a5400a" ],
	     "instanceType" : "m1.small",
	     "architecture" : "i386",
	     "version" : "2010-08-31",
	     "availabilityZone" : "us-east-1c",
	     "accountId" : "337935342288",
	     "imageId" : "ami-140eaf7d",
	     "pendingTime" : "2012-06-05T14:38:19Z",
	     "devpayProductCodes" : null,
	     "privateIp" : "10.3.94.120",
	     "region" : "us-east-1"
	   }
	"""
	implements(IFromString)
	def from_string(self, str):
		"""init self from a json string. Converts some attribute names, though."""
		import json
		dict = json.loads(str)
		map = {'instanceId': 'id', 'instanceType': 'hw_type', 'architecture': 'arch',
			'imageId': 'ami'}
		for key in dict.keys():
			if key in map:
				setattr(self, map[key], dict[key])
			else:
				setattr(self, key, dict[key])

