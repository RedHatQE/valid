IMAGES=[]
INSTANCES={}

#import ConfigParser, boto, time, fabric, image, tests, os
from fabric.api import settings, run, env, task, abort
from fabric.tasks import Task
#from ..config import AbortedConfigFile

#_example_config="""
# An example config file (~/.valigator-ec2.cfg)
#
#[Access]
# may be obtained after you log in to https://console.aws.amazon.com/
# and continue to https://aws-portal.amazon.com/gp/aws/securityCredentials
#aws_access_key_id = <your access key id>
#aws_secret_access_key = <your secret access key>
#
#[us-east-1]
# specify at least one region you would like to use
# and provide ssh key details as e.g. in
#   https://console.aws.amazon.com/ec2/home?region=us-east-1#s=KeyPairs
#key_name = <a key pair name for us-east-1>
#key_file = <location of appropriate .pem file>
#
#"""
#class AwsConfig(AbortedConfigFile):
#	"""EC2 configuration"""
#	def __init__(self):
#		AbortedConfigFile.__init__(self, os.path.expanduser('~/.valigator-ec2.cfg'))


# def _get_connection(config, region_name):
# 	"""connects to a region_name and returns the connection object. Assumes
# 	   a valid configuration file"""
# 	region = boto.ec2.get_region(region_name,
# 			aws_access_key_id=config.Access.aws_access_key_id.value,
# 			aws_secret_access_key=config.Access.aws_secret_access_key.value)
# 	if not region:
# 		abort("Unable to fetch region %s details from aws; perhaps wrong region name or key id or secret key provided." % region)
# 	connection = region.connect(aws_access_key_id=aws_id, aws_secret_access_key=aws_key)
# 	if not connection:
# 		abort("Unable to connect to region %s. " % region)
# 	return connection
# 
# @task
# def get_hosts(region, ami):
# 	env.key_filename.append('/home/mkovacik/.pem/aws-us-east-1.pem')
# 	# ami = 'ami-41d00528'
# 	
# 
# 	env.timeout = 5
# 	env.connection_attempts = 12
# 
# 	reg, conn, host = None, None, None
# 	reg = boto.ec2.get_region('us-east-1', aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
# 	if reg:
# 		#print reg.__dict__
# 		conn = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
# 	if conn:
# 		#print conn.__dict__
# 		img = image.i386Image(ami, conn, key_name)
# 		IMAGES.append(img)
# 	for hostname in img.instances.keys():
# 		env.hosts.extend([hostname])
# 
# class MT(Task):
# 	def run(self):
# 		pass

@task
def read_hosts(filename):
	"""read a csv filename containing instance details and update env.hosts
	   accordingly"""
	import instance, csv
	from fabric.api import env
	reader = csv.DictReader(open(filename))
	for line_dict in reader:
		# read all the instances
		anInstance = instance.Instance()
		for key in line_dict.keys():
			setattr(anInstance, key, line_dict[key])
			# print key, line_dict[key]
		INSTANCES[anInstance.get_host_string()] = anInstance
		# add instance access pem to the keys
		env.key_filename.append(anInstance.key_file)
	# add all the host strings into env.hosts
	env.hosts.extend(INSTANCES.keys())
	from fabric.utils import puts
	puts(env.hosts)

# introduce the tests
import osversion_test, identity_test, disk_test


