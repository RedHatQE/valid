from boto.ec2.image import Image as botoImage
from ..osversion import OSVersion
from instance import Instance

def get_image(connection, id):
	"""generates a runtime error exception in case no image found"""
	image = connection.get_image(id)
	if not image:
		raise RuntimeError("Connection %s doesn't provide image %s" % (connection, id))
	return image

def image_version_string(image_name):
	"""RHEL specific, returns version string based on an image name"""
	return str(image_name).split("-")[1]

class Image(object):
	instances = {}
	id = None
	intstance_types = []
	version = None
	def __init__(self, id, connection, key_name):
		self.id = id
		self.connection = connection
		self.image = get_image(connection, id)
		self.version = OSVersion()
		self.version.from_string(image_version_string(self.image.name))
		for instance_type in self.instance_types:
			instance = Instance(connection, key_name, self.id,
					instance_type)
			self.instances[instance.hostname] = instance
			valigator.ec2.INSTANCES[instance.hostname] = instance
			instance.image = self
	def __str__(self):
		return "%s: %s" % (self.id, self.instances)

class i386Image(Image):
	instance_types = ['t1.micro']


